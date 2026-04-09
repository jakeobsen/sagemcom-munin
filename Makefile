INSTALLDIR := $(shell pwd)
SYSTEMD_DIR ?= /etc/systemd/system
PYTHON ?= python3
VENV := $(INSTALLDIR)/.venv
MUNIN_DIR ?= /etc/munin/plugins

.PHONY: help install uninstall venv enable disable status test test-logs install-munin

help:
	@echo "Usage:"
	@echo "  make install       - Set up venv, config, systemd timers"
	@echo "  make uninstall     - Stop timers and remove systemd units"
	@echo "  make enable        - Enable and start systemd timers"
	@echo "  make disable       - Stop and disable systemd timers"
	@echo "  make status        - Show timer status"
	@echo "  make test          - Run modem_logger.py --debug once"
	@echo "  make test-logs     - Run modem_logfile.py --debug once"
	@echo "  make install-munin - Symlink munin plugin"
	@echo "  make venv          - Create venv and install dependencies only"

install: venv install-config install-systemd
	@echo ""
	@echo "Installed from $(INSTALLDIR)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit $(INSTALLDIR)/config.py and set your modem password"
	@echo "  2. make test          - verify it connects"
	@echo "  3. make enable        - start the systemd timers"
	@echo "  4. make install-munin - (optional) enable munin graphs"

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip -q
	$(VENV)/bin/pip install -r requirements.txt -q

install-config:
	@if [ ! -f config.py ]; then \
		cp config.example.py config.py; \
		echo "Created config.py — edit it with your modem password"; \
	else \
		echo "config.py already exists, not overwriting"; \
	fi

install-systemd:
	@sed 's|/opt/modem-logger|$(INSTALLDIR)|g' systemd/modem-logger.service > $(SYSTEMD_DIR)/modem-logger.service
	@sed 's|/opt/modem-logger|$(INSTALLDIR)|g' systemd/modem-logger.timer > $(SYSTEMD_DIR)/modem-logger.timer
	@sed 's|/opt/modem-logger|$(INSTALLDIR)|g' systemd/modem-logfile.service > $(SYSTEMD_DIR)/modem-logfile.service
	@sed 's|/opt/modem-logger|$(INSTALLDIR)|g' systemd/modem-logfile.timer > $(SYSTEMD_DIR)/modem-logfile.timer
	systemctl daemon-reload

enable:
	systemctl enable --now modem-logger.timer
	systemctl enable --now modem-logfile.timer

disable:
	systemctl disable --now modem-logger.timer
	systemctl disable --now modem-logfile.timer

status:
	@systemctl list-timers modem-logger.timer modem-logfile.timer
	@echo ""
	@echo "Recent logs:"
	@journalctl -u modem-logger -u modem-logfile --no-pager -n 20

test:
	$(VENV)/bin/python3 modem_logger.py --debug

test-logs:
	$(VENV)/bin/python3 modem_logfile.py --debug

install-munin:
	chmod +x munin.py
	ln -sf $(INSTALLDIR)/munin.py $(MUNIN_DIR)/modem_
	@echo "Munin plugin installed. Add to /etc/munin/plugin-conf.d/modem:"
	@echo "  [modem_*]"
	@echo "  env.db_path $(INSTALLDIR)/modem_stats.db"
	@echo ""
	@echo "Then: sudo systemctl restart munin-node"

uninstall:
	-systemctl disable --now modem-logger.timer 2>/dev/null
	-systemctl disable --now modem-logfile.timer 2>/dev/null
	rm -f $(SYSTEMD_DIR)/modem-logger.service $(SYSTEMD_DIR)/modem-logger.timer
	rm -f $(SYSTEMD_DIR)/modem-logfile.service $(SYSTEMD_DIR)/modem-logfile.timer
	rm -f $(MUNIN_DIR)/modem_
	systemctl daemon-reload
	@echo "Systemd units and munin plugin removed."
	@echo "Data and config left in $(INSTALLDIR) — remove manually if desired."
