#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main() {
    printf("[SPEECH ANALYSER] Started. PID=%d Priority=55\n", getpid());
    fflush(stdout);
    int wpm, filler_count = 0, pause_count = 0;
    while (1) {
        wpm = 100 + (rand() % 80);
        if (rand() % 5 == 0) filler_count++;
        if (rand() % 8 == 0) pause_count++;
        printf("[SPEECH ANALYSER] WPM=%d Fillers=%d Pauses=%d\n", wpm, filler_count, pause_count);
        fflush(stdout);
        sleep(2);
    }
    return 0;
}
