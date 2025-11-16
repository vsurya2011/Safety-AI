package com.app.converter.controller;

import com.app.converter.service.AudioService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Controller
public class UploadController {

    private final AudioService audioService;

    public UploadController(AudioService audioService) {
        this.audioService = audioService;
    }

    @GetMapping("/")
    public String index() {
        return "index";
    }

    @PostMapping("/convert")
    public ResponseEntity<FileSystemResource> convertFile(@RequestParam("file") MultipartFile file) throws Exception {
        var converted = audioService.convert(file);

        return ResponseEntity.ok()
                .header("Content-Disposition",
                        "attachment; filename=\"" + converted.getName() + "\"")
                .body(new FileSystemResource(converted));
    }
}
