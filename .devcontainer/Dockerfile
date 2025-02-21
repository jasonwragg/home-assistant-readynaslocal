# Home Assistant Dev Container
FROM ghcr.io/home-assistant/devcontainer:latest

# Set up environment
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

# Install dependencies
RUN pip install --no-cache-dir -r requirements_test.txt

# Set the working directory
WORKDIR /workspaces/home-assistant-readynaslocal

# Expose Home Assistant port
EXPOSE 8123
