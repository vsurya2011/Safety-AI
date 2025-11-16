package com.app.converter.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;

@Service
public class AudioService {
    public File convert(MultipartFile file) throws Exception {
        File input = File.createTempFile("input", ".m4a");
        File output = File.createTempFile("output", ".mp3");

        file.transferTo(input);

        String[] command = {
                "ffmpeg", "-y",
                "-i", input.getAbsolutePath(),
                "-c:a", "libmp3lame",
                "-b:a", "192k",
                output.getAbsolutePath()
        };

        Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
        process.waitFor();

        input.delete(); // cleanup

        return output;
    }
}
