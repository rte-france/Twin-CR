/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.telemetry;

import java.util.List;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import org.TwinCR.argus_backends.common.core.bridge.SseNatsBridge;

import io.nats.client.*;

public abstract class TelemetryConsumerCommon {
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    public TelemetryConsumerCommon(Connection conn, SseNatsBridge bridge) {}

    public abstract void acquireSubTopic(String subTopic);
    public abstract void releaseSubTopic(String subTopic);

    public void temporarilyAcquireSubTopic(String subject) {
        acquireSubTopic(subject);

        scheduler.schedule(() -> {
            try {
                releaseSubTopic(subject);
            } catch (Exception ignored) {
            }
        }, 60, TimeUnit.SECONDS);
    }

    public abstract void updateNetwork(Optional<String> subject);

    /** Prefix of the NATS subjects of the sub-topics ("<prefix>.<sub-topic>") */
    public abstract String subjectPrefix();

    /** Latest message of each id of a sub-topic, sent to new SSE subscribers after registering them */
    public abstract List<String> latestPayloads(String subTopic);
}
