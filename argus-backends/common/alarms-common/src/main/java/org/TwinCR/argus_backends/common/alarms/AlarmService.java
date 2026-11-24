/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.alarms;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import io.nats.client.Connection;
import io.nats.client.Dispatcher;

import org.TwinCR.argus_backends.common.core.bridge.DeferredSseClient;
import org.TwinCR.argus_backends.common.core.bridge.SseClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Deque;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * Alarm list and event journal of one backend, fed by the AlarmDetector of the Orchestrator (schemas/Orchestrator/Publications/alarm.json).
 *
 * Lifecycle of the alarms:
 *  - momentary: acknowledging removes the alarm;
 *  - persistent: the alarm is acknowledged, then cleared once ended (back to its normal state);
 *  - retain = false (NO RETAIN): a new state of an id replaces its alarms, else each occurrence has its own alarm.
 * Acknowledgements, clearings and comments are shared by all the clients of the backend, and logged in the event journal.
 *
 * OverloadMonitor: the monitored conditions currently on ("monitor": thresholds crossed, monitored TS not normal), by id,
 * whatever the acknowledgements; includes those already on at start ("initial", which are not alarms when momentary).
 *
 * Clients follow the state through an SSE stream: a snapshot, then the changes:
 *  {"type": "snapshot", "alarms": [...], "events": [...], "monitor": [...]}, {"type": "alarm", "alarm": {...}} (added or
 *  updated), {"type": "alarm_removed", "uid": n}, {"type": "event", "event": {...}}, {"type": "monitor", "entry": {...}}
 *  (added or updated), {"type": "monitor_removed", "id": "..."}, {"type": "keepalive"}.
 */
public class AlarmService {
    private static final Logger LOGGER = LoggerFactory.getLogger(AlarmService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final int MAX_EVENTS = 10_000;
    private static final String KEEPALIVE = "{\"type\":\"keepalive\"}";

    private final Map<Long, ObjectNode> alarms = new LinkedHashMap<>();  // By uid, in order of arrival
    private final Map<String, ObjectNode> monitor = new LinkedHashMap<>();  // OverloadMonitor: thresholds crossed, by id
    private final Deque<ObjectNode> events = new ArrayDeque<>();
    private final Set<SseClient> clients = ConcurrentHashMap.newKeySet();
    // Unique across the restarts of the backend (clients keep their uids/seqs across a reconnection)
    private long nextUid = System.currentTimeMillis() * 1000;
    private long nextSeq = System.currentTimeMillis() * 1000;
    private volatile double currentTime = 0;

    /**
     * @param subject NATS subject of the AlarmDetector for this backend ("Alarms.GameMaster" or "Alarms.HMI.<location>")
     */
    public AlarmService(Connection conn, String subject) {
        Dispatcher dispatcher = conn.createDispatcher(msg -> {
            try {
                if ("time".equals(msg.getSubject())) {
                    currentTime = MAPPER.readTree(msg.getData()).path("current_time").asDouble(currentTime);
                } else {
                    onAlarm((ObjectNode) MAPPER.readTree(msg.getData()));
                }
            } catch (Exception e) {
                LOGGER.warn("Invalid alarm message on {}", msg.getSubject(), e);
            }
        });
        dispatcher.subscribe(subject);
        dispatcher.subscribe("time");
        LOGGER.info("Alarm service subscribed to {}", subject);

        // Also detects the disconnected clients
        ScheduledExecutorService keepalive = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "alarm-keepalive");
            t.setDaemon(true);
            return t;
        });
        keepalive.scheduleAtFixedRate(() -> {
            synchronized (this) {
                broadcast(KEEPALIVE);
            }
        }, 10, 10, TimeUnit.SECONDS);
    }

    /** Handle an alarm or event published by the AlarmDetector */
    private synchronized void onAlarm(ObjectNode message) {
        boolean persistent = "persistent".equals(message.path("mode").asText());
        if (message.path("monitor").asBoolean(false) || "threshold".equals(message.path("kind").asText())) {
            updateMonitor(message);
            if (message.path("initial").asBoolean(false) && !persistent) {
                return;  // Already on at start: in the OverloadMonitor only, neither an alarm nor a change
            }
        }

        ObjectNode event = MAPPER.createObjectNode();
        event.put("seq", nextSeq++);
        for (String field : List.of("time", "id", "label", "state", "kind", "alarm", "priority", "color", "equipment_id", "side", "substation_id")) {
            if (message.has(field)) {
                event.set(field, message.get(field));
            }
        }
        addEvent(event);

        String id = message.path("id").asText();
        // An event (even with "alarm": false) can end an alarm
        if (persistent && message.path("normal").asBoolean(false)) {
            // End of the persistent alarms of this id: they can now be cleared
            for (ObjectNode alarm : alarms.values()) {
                if (alarm.path("id").asText().equals(id) && !alarm.path("ended").asBoolean()) {
                    alarm.put("ended", true);
                    alarm.put("end_time", message.path("time").asDouble());
                    broadcastAlarm(alarm);
                }
            }
            return;
        }
        // Only an event ("alarm": false), skip
        if (!message.path("alarm").asBoolean(false)) {
            return;
        }
        if (!message.path("retain").asBoolean(true)) {
            // NO RETAIN: only the latest state of the id is kept
            removeAlarms(alarms.values().stream().filter(a -> a.path("id").asText().equals(id)).map(a -> a.path("uid").asLong()).toList());
        }

        ObjectNode alarm = message.deepCopy();
        alarm.put("uid", nextUid++);
        alarm.put("acked", false);
        alarm.put("ended", !persistent);  // Only persistent alarms have to end before being cleared
        alarm.putNull("comment");
        alarms.put(alarm.path("uid").asLong(), alarm);
        broadcastAlarm(alarm);
    }

    /**
     * Acknowledge alarms: removes the momentary ones, the persistent ones then have to be cleared
     * @return the uids acknowledged
     */
    public synchronized List<Long> acknowledge(Collection<Long> uids) {
        List<Long> done = new ArrayList<>();
        for (Long uid : uids) {
            ObjectNode alarm = alarms.get(uid);
            if (alarm == null || alarm.path("acked").asBoolean()) {
                continue;
            }
            done.add(uid);
            logAction(alarm, "acknowledge", "Acknowledged");
            if ("persistent".equals(alarm.path("mode").asText())) {
                alarm.put("acked", true);
                broadcastAlarm(alarm);
            } else {
                removeAlarms(List.of(uid));
            }
        }
        return done;
    }

    /**
     * Clear persistent alarms, once acknowledged and ended
     * @return the uids cleared
     */
    public synchronized List<Long> clear(Collection<Long> uids) {
        List<Long> done = new ArrayList<>();
        for (Long uid : uids) {
            ObjectNode alarm = alarms.get(uid);
            if (alarm == null || !alarm.path("acked").asBoolean() || !alarm.path("ended").asBoolean()) {
                continue;
            }
            done.add(uid);
            logAction(alarm, "clear", "Cleared");
            removeAlarms(List.of(uid));
        }
        return done;
    }

    /**
     * Set (or remove, with null or blank) the comment of an alarm. The comment disappears with the alarm.
     * @return false if the alarm does not exist
     */
    public synchronized boolean comment(long uid, String comment) {
        ObjectNode alarm = alarms.get(uid);
        if (alarm == null) {
            return false;
        }
        if (comment == null || comment.isBlank()) {
            alarm.putNull("comment");
            logAction(alarm, "comment", "Comment removed");
        } else {
            alarm.put("comment", comment);
            logAction(alarm, "comment", "Comment: " + comment);
        }
        broadcastAlarm(alarm);
        return true;
    }

    /** Current alarms and events */
    public synchronized ObjectNode snapshot() {
        ObjectNode snapshot = MAPPER.createObjectNode();
        snapshot.put("type", "snapshot");
        ArrayNode alarmArray = snapshot.putArray("alarms");
        alarms.values().forEach(alarmArray::add);
        ArrayNode eventArray = snapshot.putArray("events");
        events.forEach(eventArray::add);
        ArrayNode monitorArray = snapshot.putArray("monitor");
        monitor.values().forEach(monitorArray::add);
        return snapshot;
    }

    /** OverloadMonitor: a monitored condition on is added or updated (keeping the time it started), removed when back to normal */
    private void updateMonitor(ObjectNode message) {
        String id = message.path("id").asText();
        if (message.path("normal").asBoolean(false)) {
            if (monitor.remove(id) != null) {
                ObjectNode removed = MAPPER.createObjectNode();
                removed.put("type", "monitor_removed");
                removed.put("id", id);
                broadcast(removed.toString());
            }
            return;
        }
        ObjectNode entry = MAPPER.createObjectNode();
        for (String field : List.of("id", "label", "state", "value", "limit", "time", "priority", "color", "equipment_id", "side", "substation_id")) {
            if (message.has(field)) {
                entry.set(field, message.get(field));
            }
        }
        entry.put("since", monitor.containsKey(id) ? monitor.get(id).path("since").asDouble() : message.path("time").asDouble());
        monitor.put(id, entry);
        ObjectNode update = MAPPER.createObjectNode();
        update.put("type", "monitor");
        update.set("entry", entry);
        broadcast(update.toString());
    }

    /** Send the snapshot to a new client, then the changes */
    public void register(SseClient client) throws IOException {
        DeferredSseClient deferred = new DeferredSseClient(client);
        QueuedClient queued = new QueuedClient(deferred);
        String snapshot;
        synchronized (this) {
            snapshot = snapshot().toString();
            clients.add(queued);
        }
        try {
            deferred.start(List.of(snapshot));
        } catch (IOException e) {
            clients.remove(queued);
            queued.close();
            throw e;
        }
    }

    private void logAction(ObjectNode alarm, String kind, String state) {
        ObjectNode event = MAPPER.createObjectNode();
        event.put("seq", nextSeq++);
        event.put("time", currentTime);
        for (String field : List.of("id", "label", "equipment_id", "side", "substation_id")) {
            if (alarm.has(field)) {
                event.set(field, alarm.get(field));
            }
        }
        event.put("state", state);
        event.put("kind", kind);
        event.put("alarm", false);
        event.put("priority", 0);
        event.put("color", "grey");
        event.put("uid", alarm.path("uid").asLong());
        addEvent(event);
    }

    private void addEvent(ObjectNode event) {
        events.addLast(event);
        while (events.size() > MAX_EVENTS) {
            events.removeFirst();
        }
        ObjectNode message = MAPPER.createObjectNode();
        message.put("type", "event");
        message.set("event", event);
        broadcast(message.toString());
    }

    private void removeAlarms(List<Long> uids) {
        for (Long uid : uids) {
            if (alarms.remove(uid) != null) {
                broadcast("{\"type\":\"alarm_removed\",\"uid\":" + uid + "}");
            }
        }
    }

    private void broadcastAlarm(ObjectNode alarm) {
        ObjectNode message = MAPPER.createObjectNode();
        message.put("type", "alarm");
        message.set("alarm", alarm);
        broadcast(message.toString());
    }

    /** Called with the lock held, so that all the clients get the changes in the same order; only queues the sending */
    private void broadcast(String payload) {
        Iterator<SseClient> it = clients.iterator();
        while (it.hasNext()) {
            SseClient client = it.next();
            try {
                client.send(payload);
            } catch (IOException e) {
                it.remove();
            }
        }
    }

    /**
     * Sends to one client from its own thread, so that a slow or stalled client delays neither the others nor the alarm
     * processing (which queues under the lock). A client that fails, or falls MAX_QUEUED messages behind, is closed: it
     * is removed on the next broadcast (at least every keepalive) and resynchronises with a snapshot when it reconnects.
     */
    private static final class QueuedClient implements SseClient {
        private static final int MAX_QUEUED = 10_000;
        private final SseClient delegate;
        private final ThreadPoolExecutor executor;
        private volatile boolean closed = false;

        QueuedClient(SseClient delegate) {
            this.delegate = delegate;
            this.executor = new ThreadPoolExecutor(1, 1, 0, TimeUnit.MILLISECONDS, new LinkedBlockingQueue<>(MAX_QUEUED), r -> {
                Thread t = new Thread(r, "alarm-sse");
                t.setDaemon(true);
                return t;
            });
        }

        @Override
        public void send(String data) throws IOException {
            if (closed) {
                throw new IOException("Alarm SSE client closed");
            }
            try {
                executor.execute(() -> {
                    if (closed) {
                        return;
                    }
                    try {
                        delegate.send(data);
                    } catch (IOException e) {
                        close();
                    }
                });
            } catch (RejectedExecutionException e) {
                close();
                throw new IOException("Alarm SSE client too slow, dropped", e);
            }
        }

        @Override
        public void close() {
            if (closed) {
                return;
            }
            closed = true;
            executor.shutdownNow();
            // Ends the HTTP stream so that the client reconnects (and gets a snapshot). Own thread: may be called with
            // the service lock held, while the sending thread is blocked in a write
            Thread.startVirtualThread(delegate::close);
        }
    }
}
