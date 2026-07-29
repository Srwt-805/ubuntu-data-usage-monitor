.PHONY: all install update run uninstall reinstall help

# Default target
all: install

# Install or update the application
install:
	@chmod +x install.sh
	@./install.sh

# Alias for install
update: install

# Launch the application from the installed location
run:
	@if [ -f "$$HOME/.local/share/vstat/run.sh" ]; then \
		$$HOME/.local/share/vstat/run.sh; \
	else \
		echo "Data Usage Monitor is not installed."; \
		echo "Run: make"; \
	fi

# Uninstall from the installed location
uninstall:
	@if [ -f "$$HOME/.local/share/vstat/uninstall.sh" ]; then \
		chmod +x "$$HOME/.local/share/vstat/uninstall.sh"; \
		$$HOME/.local/share/vstat/uninstall.sh; \
	else \
		echo "Data Usage Monitor is not installed."; \
	fi

# Reinstall
reinstall: uninstall install

# Help
help:
	@echo ""
	@echo "Data Usage Monitor"
	@echo "=================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  make            Install or update Data Usage Monitor"
	@echo "  make install    Install or update"
	@echo "  make update     Update existing installation"
	@echo "  make run        Run the installed application"
	@echo "  make uninstall  Remove Data Usage Monitor"
	@echo "  make reinstall  Reinstall Data Usage Monitor"
	@echo "  make help       Show this help"
	@echo ""