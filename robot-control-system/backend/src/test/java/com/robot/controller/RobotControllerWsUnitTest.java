package com.robot.controller;

import com.robot.model.ControlCommand;
import com.robot.service.SerialPortService;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.Arrays;

class RobotControllerWsUnitTest {

    @Test
    void moveToAnglesAbsMultiple() {
        SerialPortService sps = Mockito.mock(SerialPortService.class);
        RobotController controller = new RobotController(sps);
        ControlCommand cmd = new ControlCommand();
        cmd.setType("move_to_angles");
        cmd.setMode("abs");
        cmd.setAngles(Arrays.asList(10.0, 20.0, null, -5.5));
        controller.handleControl(cmd);
        Mockito.verify(sps).sendAbsRotate(1, 10.0);
        Mockito.verify(sps).sendAbsRotate(2, 20.0);
        Mockito.verify(sps).sendAbsRotate(4, -5.5);
        Mockito.verifyNoMoreInteractions(sps);
    }

    @Test
    void moveToAnglesRelSingle() {
        SerialPortService sps = Mockito.mock(SerialPortService.class);
        RobotController controller = new RobotController(sps);
        ControlCommand cmd = new ControlCommand();
        cmd.setType("move_to_angles");
        cmd.setMode("rel");
        cmd.setJointId(3);
        cmd.setAngle(15.25);
        controller.handleControl(cmd);
        Mockito.verify(sps).sendRelRotate(3, 15.25);
        Mockito.verifyNoMoreInteractions(sps);
    }
}

