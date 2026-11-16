/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.bridge;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * SSE client that holds back the live messages until its initial messages (e.g. latest values) are sent.
 * Registered before the initial messages are fetched, so that no live message is missed, and sending them before
 * the held-back live messages, which are more recent, so that a client never receives an older value after a newer one.
 */
public class DeferredSseClient implements SseClient {
    private final SseClient delegate;
    private List<String> pending = new ArrayList<>();  // Held-back live messages, null once started

    public DeferredSseClient(SseClient delegate) {
        this.delegate = delegate;
    }

    @Override
    public void send(String data) throws IOException {
        synchronized (this) {
            if (pending != null) {
                pending.add(data);
                return;
            }
        }
        delegate.send(data);
    }

    /** Sends the initial messages, then the live messages held back meanwhile, then sends the live messages directly */
    public void start(List<String> initialMessages) throws IOException {
        for (String data : initialMessages) {
            delegate.send(data);
        }
        // Drain outside the lock, so that live messages of other clients are not blocked while sending
        while (true) {
            List<String> batch;
            synchronized (this) {
                if (pending.isEmpty()) {
                    pending = null;
                    return;
                }
                batch = pending;
                pending = new ArrayList<>();
            }
            for (String data : batch) {
                delegate.send(data);
            }
        }
    }
}
