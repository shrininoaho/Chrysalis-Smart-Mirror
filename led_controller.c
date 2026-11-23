#include <stdio.h>
#include <unistd.h>

int main() {
    printf("[LED CONTROLLER] Started. PID=%d Priority=35\n", getpid());
    fflush(stdout);
    char *colors[] = {"GREEN (120-160 WPM)", "RED (too slow)", "AMBER (too fast)", "PURPLE (filler word)", "BLUE (pause)"};
    int i = 0;
    while (1) {
        printf("[LED CONTROLLER] LED colour -> %s\n", colors[i % 5]);
        fflush(stdout);
        i++;
        sleep(3);
    }
    return 0;
}
