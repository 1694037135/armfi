package com.robot.controller;

import com.robot.service.SerialPortService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(RobotController.class)
class RobotControllerRestTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private SerialPortService serialPortService;

    @Test
    void statusEndpoint() throws Exception {
        Mockito.when(serialPortService.isConnected()).thenReturn(false);
        mockMvc.perform(get("/api/status"))
                .andExpect(status().isOk())
                .andExpect(content().string("disconnected"));
        Mockito.when(serialPortService.isConnected()).thenReturn(true);
        mockMvc.perform(get("/api/status"))
                .andExpect(status().isOk())
                .andExpect(content().string("connected"));
    }

    @Test
    void testEndpoint() throws Exception {
        mockMvc.perform(post("/api/test"))
                .andExpect(status().isOk())
                .andExpect(content().string("测试命令已发送"));
        Mockito.verify(serialPortService).sendCommand("soft_reset");
    }
}

