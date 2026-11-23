#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

#define NUM_PROCESSES 3

typedef struct {
    char *name;
    char *path;
    pid_t pid;
} ManagedProcess;

ManagedProcess processes[NUM_PROCESSES] = {
    {"SPEECH ANALYSER", "./speech_analyser", -1},
    {"LED CONTROLLER",  "./led_controller",  -1},
    {"SESSION LOGGER",  "./session_logger",  -1},
};

pid_t spawn_process(ManagedProcess *p) {
    pid_t pid = fork();
    if (pid == 0) {
        execl(p->path, p->path, (char *)NULL);
        perror("execl failed");
        exit(1);
    }
    return pid;
}

int main() {
    printf("================================================\n");
    printf("  REAL-TIME PUBLIC SPEAKING COACH - QNX RTOS\n");
    printf("  Watchdog started. PID=%d\n", getpid());
    printf("================================================\n");
    fflush(stdout);

    for (int i = 0; i < NUM_PROCESSES; i++) {
        processes[i].pid = spawn_process(&processes[i]);
        printf("[WATCHDOG] Started %s PID=%d\n", processes[i].name, processes[i].pid);
        fflush(stdout);
        usleep(200000);
    }
    printf("\n[WATCHDOG] All processes running. Monitoring...\n\n");
    fflush(stdout);

    while (1) {
        sleep(1);
        for (int i = 0; i < NUM_PROCESSES; i++) {
            int status;
            pid_t result = waitpid(processes[i].pid, &status, WNOHANG);
            if (result == processes[i].pid || result == -1) {
                printf("\n[WATCHDOG] *** ALERT: %s (PID=%d) CRASHED ***\n", processes[i].name, processes[i].pid);
                printf("[WATCHDOG] Restarting %s...\n", processes[i].name);
                fflush(stdout);
                processes[i].pid = spawn_process(&processes[i]);
                printf("[WATCHDOG] %s RESTARTED with PID=%d\n\n", processes[i].name, processes[i].pid);
                fflush(stdout);
            }
        }
    }
    return 0;
}
