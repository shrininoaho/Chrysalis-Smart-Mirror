#include <stdio.h>
#include <unistd.h>

int main() {
    printf("[SESSION LOGGER] Started. PID=%d Priority=20\n", getpid());
    fflush(stdout);
    int elapsed = 0;
    while (1) {
        elapsed += 5;
        printf("[SESSION LOGGER] Session running... elapsed=%ds words=~%d\n", elapsed, elapsed * 2);
        fflush(stdout);
        sleep(5);
    }
    return 0;
}
