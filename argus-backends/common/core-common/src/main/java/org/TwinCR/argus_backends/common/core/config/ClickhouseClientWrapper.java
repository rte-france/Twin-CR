/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.config;

public class ClickhouseClientWrapper {
    private final String host;
    private final int port;
    private final String simulationId;

    public ClickhouseClientWrapper(String host, int port, String simulationId) {
        this.host = host;
        this.port = port;
        this.simulationId = simulationId;
    }

    public byte[] getFileContent(String path) {
        try {
            String query = String.format(
                "SELECT content FROM `%s`.InputFiles WHERE input_file = '%s' FORMAT RowBinary",
                simulationId,
                path
            );

            // Using curl instead of the java Clickhouse client because it causes encoding isues https://github.com/ClickHouse/clickhouse-java/issues/2263
            String url = "http://" + host + ":" + port;
            java.net.URI uri = java.net.URI.create(url);
            java.net.HttpURLConnection connection = (java.net.HttpURLConnection) uri.toURL().openConnection();
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);

            // Write query
            try (java.io.OutputStream os = connection.getOutputStream()) {
                os.write(query.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            }

            try (java.io.InputStream in = connection.getInputStream()) {
                // Decode RowBinary varint length
                long length = 0;
                int shift = 0;
                int b;

                do {
                    b = in.read();
                    if (b == -1) {
                        throw new IllegalStateException("Unexpected end of stream while reading length");
                    }
                    length |= (long) (b & 0x7F) << shift;
                    shift += 7;
                } while ((b & 0x80) != 0);

                if (length > Integer.MAX_VALUE) {
                    throw new IllegalStateException("File too large: " + length);
                }

                // Write output of size 'length'
                byte[] data = new byte[(int) length];

                int offset = 0;
                while (offset < data.length) {
                    int read = in.read(data, offset, data.length - offset);
                    if (read == -1) {
                        throw new IllegalStateException("Unexpected end of stream while reading file content");
                    }
                    offset += read;
                }
            return data;
            }

        } catch (Exception e) {
            throw new IllegalStateException("Failed to fetch file from ClickHouse: " + path, e);
        }
    }
}
