# Gmail Blaxel Sandbox

<p align="center">
  <img src="https://blaxel.ai/logo.png" alt="Blaxel" width="200"/>
</p>

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-container-blue.svg)](https://www.docker.com/)
[![Blaxel](https://img.shields.io/badge/Blaxel-Sandbox-brightgreen.svg)](https://blaxel.ai/)

</div>

A specialized Blaxel sandbox for synthetically generating Gmail data in a mocked environment. This sandbox allows AI agents to write flexible code that seeds realistic Gmail scenarios (messages, drafts, threads) for testing and development purposes.

**Inspired by:**
- [Klavis AI Gmail Sandbox](https://www.klavis.ai/docs/api-reference/sandbox/gmail/initialize-gmail) - Data structure and API design
- [Anthropic Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) - Code-based flexibility approach

## 📑 Table of Contents

- [✨ Features](#features)
- [📧 Gmail Sandbox API](#gmail-sandbox-api)
- [🚀 Quick Start](#quick-start)
- [📋 Prerequisites](#prerequisites)
- [💻 Installation](#installation)
- [🔧 Usage](#usage)
  - [Running Locally with Docker](#running-locally-with-docker)
  - [Deploying to Blaxel](#deploying-to-blaxel)
  - [Connecting to Sandbox](#connecting-to-sandbox)
- [📁 Project Structure](#project-structure)
- [❓ Troubleshooting](#troubleshooting)
- [👥 Contributing](#contributing)
- [🆘 Support](#support)
- [📄 License](#license)

## ✨ Features

- **Gmail Sandbox API** - Code-based API for synthetically generating Gmail data
- **Flexible Data Generation** - Write custom code to create messages, drafts, and threads
- **Realistic Test Scenarios** - Helper functions for generating bulk test data
- **TypeScript Support** - Fully typed API with comprehensive type definitions
- **Containerized Environment** - Secure sandbox for code execution
- **Blaxel Platform Integration** - Seamless cloud deployment
- **Future Supabase Integration** - Placeholder logic for database persistence
- **Agent-Friendly** - Designed for AI agents to write flexible seeding code

## 📧 Gmail Sandbox API

The Gmail Sandbox API provides a code-based approach for AI agents to synthetically generate Gmail data. Instead of making direct API calls, agents write TypeScript code using our methods to create complex, realistic Gmail environments.

### Quick Example

```typescript
import { initializeGmailSandbox, generateTestMessages } from './src/gmail';

// Create a sandbox with 50 test messages
const messages = generateTestMessages(50, {
  labels: ['INBOX'],
  fromDomain: 'company.com',
  toDomain: 'company.com'
});

const response = await initializeGmailSandbox('my-sandbox', {
  messages
});

console.log(`Created ${response.records_created.messages} messages`);
```

### Supported Operations

- **Messages**: Create, read, list, delete, update labels
- **Drafts**: Create, read, list, update, delete, send
- **Bulk Operations**: Generate and create data in bulk
- **Helper Functions**: Automatically generate realistic test data

### Documentation

For complete API documentation, examples, and usage guides, see:

**[Gmail Sandbox API Documentation](./GMAIL_API.md)**

The documentation includes:
- Complete API reference with all methods and types
- 7 detailed usage examples
- Advanced patterns (threads, bulk generation, custom logic)
- Future database schema design

## 🚀 Quick Start

For those who want to get up and running quickly:

```bash
# Or use blaxel CLI
bl create-sandbox YOUR-SANDBOX-NAME -y -t template-sandbox-codegen

# Navigate to the project directory
cd template-sandbox-claude-code

# Deploy to Blaxel
bl deploy

# Wait for your sandbox to be deployed
bl get sandbox YOUR-SANDBOX-NAME --watch

# Connect to your deployed sandbox
bl connect sandbox YOUR-SANDBOX-NAME
```

## 📋 Prerequisites

- **Blaxel Platform Setup:** Complete Blaxel setup by following the [quickstart guide](https://docs.blaxel.ai/Get-started#quickstart)
  - **[Blaxel CLI](https://docs.blaxel.ai/Get-started):** Ensure you have the Blaxel CLI installed. If not, install it globally:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/blaxel-ai/toolkit/main/install.sh | BINDIR=/usr/local/bin sudo -E sh
    ```
  - **Blaxel login:** Login to Blaxel platform
    ```bash
    bl login YOUR-WORKSPACE
    ```

## 💻 Installation

**Clone the repository:**

```bash
git clone https://github.com/blaxel-ai/template-sandbox-claude-code.git
cd template-sandbox-claude-code
```

No additional dependencies need to be installed as everything runs in containers.

## 🔧 Usage

### Running Locally with Docker

Build and run the sandbox container locally:

```bash
# Build the Docker image
make build

# Run the container
make run
```

This will start the sandbox environment with ports 8080 and 3000 exposed for development.

### Deploying to Blaxel

When you are ready to deploy your sandbox to the cloud:

```bash
bl deploy
```

This command uses your code and the configuration in `blaxel.toml` to deploy your sandbox environment on the Blaxel platform.

### Connecting to Sandbox

Once deployed, you can connect to your sandbox:

```bash
bl connect sandbox YOUR-SANDBOX-NAME
```

Replace `YOUR-SANDBOX-NAME` with the actual name of your deployed sandbox.

## 📁 Project Structure

```
gmail/
├── src/
│   └── gmail/
│       ├── types.ts       # TypeScript type definitions for Gmail objects
│       ├── messages.ts    # API methods for Gmail messages
│       ├── drafts.ts      # API methods for Gmail drafts
│       └── index.ts       # Main initialization module and exports
├── examples/
│   └── seed-gmail.ts      # 7 comprehensive usage examples
├── Dockerfile             # Container configuration for the sandbox
├── Makefile               # Build and run commands for local development
├── entrypoint.sh          # Container startup script
├── blaxel.toml            # Blaxel deployment configuration
├── GMAIL_API.md           # Complete API documentation
└── README.md              # This file
```

## ❓ Troubleshooting

### Common Issues

1. **Docker Issues**:
   - Ensure Docker is running and accessible
   - Try `docker --version` to verify Docker installation
   - Check that ports 8080 and 3000 are available

2. **Blaxel Platform Issues**:
   - Ensure you're logged in to your workspace: `bl login MY-WORKSPACE`
   - Verify sandbox deployment: `bl get sandboxes`
   - Check deployment status: `bl logs sandbox YOUR-SANDBOX-NAME`

3. **Connection Issues**:
   - Verify the sandbox is running: `bl get sandboxes`
   - Check sandbox logs for errors: `bl logs sandbox YOUR-SANDBOX-NAME`
   - Ensure your Blaxel CLI is up to date

For more help, please [submit an issue](https://github.com/blaxel-templates/template-sandbox-claude-code/issues) on GitHub.

## 👥 Contributing

Contributions are welcome! Here's how you can contribute:

1. **Fork** the repository
2. **Create** a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** your changes:
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push** to the branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Submit** a Pull Request

Please make sure to test your changes with both local Docker and Blaxel deployment.

## 🆘 Support

If you need help with this template:

- [Submit an issue](https://github.com/blaxel-templates/template-sandbox-claude-code/issues) for bug reports or feature requests
- Visit the [Blaxel Documentation](https://docs.blaxel.ai) for platform guidance
- Check the [Blaxel Sandbox Documentation](https://docs.blaxel.ai/sandbox) for sandbox-specific help
- Join our [Discord Community](https://discord.gg/G3NqzUPcHP) for real-time assistance

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.