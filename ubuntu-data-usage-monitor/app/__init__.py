#!/usr/bin/env python3
"""Data Usage Monitor for Linux."""

from app.application import VStatApp


def main():
    app = VStatApp()
    app.run()


if __name__ == "__main__":
    main()
