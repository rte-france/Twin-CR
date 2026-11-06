/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.util;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

import org.tukaani.xz.XZInputStream;

import com.github.luben.zstd.ZstdInputStream;

public class FileLoader {
    // Load an eventually compressed file
    public static String load(Path name) {
        try (InputStream is = open(name)) {
            return new String(is.readAllBytes());
        } catch (Exception e) {
            throw new RuntimeException("Failed to load file: " + name, e);
        }
    }

    // Return a decompressed stream from an eventually compressed file. To be prefered over raw load(Path name) for large files
    public static InputStream open(Path name) {
        String fileName = name.getFileName().toString().toLowerCase();
        InputStream is = null;
        try {
            is = new BufferedInputStream(Files.newInputStream(name), 1 << 16);
            if (fileName.endsWith(".xz")) {
                return new XZInputStream(is);
            } else if (fileName.endsWith(".zst")) {
                return new ZstdInputStream(is);
            }
            return is;
        } catch (IOException e) {
            closeQuietly(is);
            throw new RuntimeException("Failed to open file: " + name, e);
        }
    }

    private static void closeQuietly(InputStream is) {
        if (is != null) {
            try {
                is.close();
            } catch (IOException ignored) {
                // Quietly
            }
        }
    }
}
