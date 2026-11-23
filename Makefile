all: watchdog speech_analyser led_controller session_logger

watchdog: watchdog.c
	qcc -o watchdog watchdog.c

speech_analyser: speech_analyser.c
	qcc -o speech_analyser speech_analyser.c

led_controller: led_controller.c
	qcc -o led_controller led_controller.c

session_logger: session_logger.c
	qcc -o session_logger session_logger.c

clean:
	rm -f watchdog speech_analyser led_controller session_logger
