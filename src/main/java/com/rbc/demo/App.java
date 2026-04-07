package com.rbc.demo;

import org.apache.commons.lang3.StringUtils;

public class App {
    public static void main(String[] args) {
        String text = "  RBC DevOps Portfolio  ";
        System.out.println("Cleaned Text: " + StringUtils.trim(text));
    }
}
