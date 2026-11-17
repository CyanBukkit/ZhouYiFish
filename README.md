# ZhouYiFish

ZhouYiFish is an experimental Chinese workbench for a person archive, four pillars, separated facts and hypotheses, a relationship graph, and a small round-table. It keeps the upstream [MiroFish](https://github.com/666ghj/MiroFish) application (AGPL-3.0) at `/mirofish`. A chart does not determine an occupation, and no accuracy gain has been shown.

```bash
chmod +x scripts/start-zhouyi.sh
./scripts/start-zhouyi.sh
```

Open `http://127.0.0.1:3000/`. The API is on port 5001 and the dev server proxies `/api`. Copy `.env.example` to `.env` only when you want a server-side key. Leave `ZHOUYI_LLM_API_KEY` empty to use charts, archives, the graph, and history. The settings page can hold a key in process memory; it is not returned, logged, or stored in the browser.

| Implemented | Not done or not passed |
| --- | --- |
| New home, archive form, four pillars, fact/hypothesis columns, editable graph, history, JSON/Markdown export | Real model end-to-end. This cloud run has no key, so analysis fails closed |
| SQLite. Health, charts, and archives start with no LLM or Zep key | OASIS swarm and Zep memory. The round table is `zhouyi_roundtable_v1` |
| OpenAI-compatible settings for `mimo-v2.6-pro` and `gpt-6-astra`, default endpoint `http://m4.cyanbukkit.cn:3000/v1`, masked key, one connection test | True solar time, 子初 day boundary, accuracy against real outcomes |
| Four arms: no chart, own chart, no-self-pair shuffled chart, equal-byte neutral text. v1 shuffle file is unchanged | The 2026-11-17 user-host probe (4 HTTP 500s, no body) is a separate machine and does not show this UI calling the endpoint |

Configuration order is in the model page: request model, process memory, `ZHOUYI_LLM_*`, then `LLM_API_KEY` only. `LLM_BASE_URL` is not reused. HTTP endpoints show one plaintext warning. Each run accepts at most 60 calls and can be cancelled. Simulated text is not an accuracy score.

The 2026-11-17 records of the two separate environments remain in [docs/runs/2026-11-17/README.md](docs/runs/2026-11-17/README.md). Research notes stay in [research/README.md](research/README.md).

The MiroFish documentation follows.

| Item | Status |
| --- | --- |
| Fictional people and four pillars | Engineering demo in `research/sandbox/EXAMPLE.md` |
| Traditional imagery | A human-written candidate list, not a classical quotation and not a fact |
| Same background with, without, and shuffled charts | Offline inputs in `research/experiments/persona_sandbox_v1/result.json` |
| Four model arms and OASIS | Comparison not run. A later user-host probe is recorded separately and did not score |
| 2026-11-17 run records | Two independent checks: four HTTP 500 probes on the user machine, and a cloud UI failure. [docs/runs/2026-11-17/README.md](docs/runs/2026-11-17/README.md) |
| Consented future behavior | Not provided, so real validation is blocked |
| Public historical people | Sourced examples only. No four pillars when historical time conversion is unsettled. Not a blind test |
| Weather trial | Historical out-of-scope audit, not the core result |

Reproduce with `python3 -m pip install -r research/requirements.txt`, then `python3 -m research.cli persona-demo` and `python3 -m research.cli persona-experiment`. `python3 -m research.cli llm-diagnose` reports whether the named variable exists and does not print secrets. Details are in [research/README.md](research/README.md).

The MiroFish documentation follows.

<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

<a href="https://trendshift.io/repositories/16144" target="_blank"><img src="https://trendshift.io/api/badge/repositories/16144" alt="666ghj%2FMiroFish | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

简洁通用的群体智能引擎，预测万物
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

<a href="https://www.shanda.com/" target="_blank"><img src="./static/image/shanda_logo.png" alt="666ghj%2FMiroFish | Shanda" height="40"/></a>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square&color=DAA520)](https://github.com/666ghj/MiroFish/stargazers)
[![GitHub Watchers](https://img.shields.io/github/watchers/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/watchers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/666ghj/MiroFish)

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord&logoColor=white)](http://discord.gg/ePf5aPaHnA)
[![X](https://img.shields.io/badge/X-Follow-000000?style=flat-square&logo=x&logoColor=white)](https://x.com/mirofish_ai)
[![Instagram](https://img.shields.io/badge/Instagram-Follow-E4405F?style=flat-square&logo=instagram&logoColor=white)](https://www.instagram.com/mirofish_ai/)

[English](./README.md) | [中文文档](./README-ZH.md)

</div>

## ⚡ Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution. You can inject variables dynamically from a "God's-eye view" to precisely deduce future trajectories — **rehearse the future in a digital sandbox, and win decisions after countless simulations**.

> You only need to: Upload seed materials (data analysis reports or interesting novel stories) and describe your prediction requirements in natural language</br>
> MiroFish will return: A detailed prediction report and a deeply interactive high-fidelity digital world

### Our Vision

MiroFish is dedicated to creating a swarm intelligence mirror that maps reality. By capturing the collective emergence triggered by individual interactions, we break through the limitations of traditional prediction:

- **At the Macro Level**: We are a rehearsal laboratory for decision-makers, allowing policies and public relations to be tested at zero risk
- **At the Micro Level**: We are a creative sandbox for individual users — whether deducing novel endings or exploring imaginative scenarios, everything can be fun, playful, and accessible

From serious predictions to playful simulations, we let every "what if" see its outcome, making it possible to predict anything.

## 🌐 Live Demo

Welcome to visit our online demo environment and experience a prediction simulation on trending public opinion events we've prepared for you: [mirofish-live-demo](https://666ghj.github.io/mirofish-demo/)

## 📸 Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/运行截图1.png" alt="Screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图2.png" alt="Screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图3.png" alt="Screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图4.png" alt="Screenshot 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/运行截图5.png" alt="Screenshot 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/运行截图6.png" alt="Screenshot 6" width="100%"/></td>
</tr>
</table>
</div>

## 🎬 Demo Videos

### 1. Wuhan University Public Opinion Simulation + MiroFish Project Introduction

<div align="center">
<a href="https://www.bilibili.com/video/BV1VYBsBHEMY/" target="_blank"><img src="./static/image/武大模拟演示封面.png" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch the complete demo video for prediction using BettaFish-generated "Wuhan University Public Opinion Report"
</div>

### 2. Dream of the Red Chamber Lost Ending Simulation

<div align="center">
<a href="https://www.bilibili.com/video/BV1cPk3BBExq" target="_blank"><img src="./static/image/红楼梦模拟推演封面.jpg" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch MiroFish's deep prediction of the lost ending based on hundreds of thousands of words from the first 80 chapters of "Dream of the Red Chamber"
</div>

> **Financial Prediction**, **Political News Prediction** and more examples coming soon...

## 🔄 Workflow

1. **Graph Building**: Seed extraction & Individual/collective memory injection & GraphRAG construction
2. **Environment Setup**: Entity relationship extraction & Persona generation & Agent configuration injection
3. **Simulation**: Dual-platform parallel simulation & Auto-parse prediction requirements & Dynamic temporal memory updates
4. **Report Generation**: ReportAgent with rich toolset for deep interaction with post-simulation environment
5. **Deep Interaction**: Chat with any agent in the simulated world & Interact with ReportAgent

## 🚀 Quick Start

### Option 1: Source Code Deployment (Recommended)

#### Prerequisites

| Tool | Version | Description | Check Installation |
|------|---------|-------------|-------------------|
| **Node.js** | 18+ | Frontend runtime, includes npm | `node -v` |
| **Python** | ≥3.11, ≤3.12 | Backend runtime | `python --version` |
| **uv** | Latest | Python package manager | `uv --version` |

#### 1. Configure Environment Variables

```bash
# Copy the example configuration file
cp .env.example .env

# Edit the .env file and fill in the required API keys
```

**Required Environment Variables:**

```env
# LLM API Configuration (supports any LLM API with OpenAI SDK format)
# Recommended: Alibaba Qwen-plus model via Bailian Platform: https://bailian.console.aliyun.com/
# High consumption, try simulations with fewer than 40 rounds first
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep Cloud Configuration
# Free monthly quota is sufficient for simple usage: https://app.getzep.com/
ZEP_API_KEY=your_zep_api_key
```

#### 2. Install Dependencies

```bash
# One-click installation of all dependencies (root + frontend + backend)
npm run setup:all
```

Or install step by step:

```bash
# Install Node dependencies (root + frontend)
npm run setup

# Install Python dependencies (backend, auto-creates virtual environment)
npm run setup:backend
```

#### 3. Start Services

```bash
# Start both frontend and backend (run from project root)
npm run dev
```

**Service URLs:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

**Start Individually:**

```bash
npm run backend   # Start backend only
npm run frontend  # Start frontend only
```

### Option 2: Docker Deployment

```bash
# 1. Configure environment variables (same as source deployment)
cp .env.example .env

# 2. Pull image and start
docker compose up -d
```

Reads `.env` from root directory by default, maps ports `3000 (frontend) / 5001 (backend)`

> Mirror address for faster pulling is provided as comments in `docker-compose.yml`, replace if needed.

## 📬 Join the Conversation

<div align="center">
<img src="./static/image/QQ群.png" alt="QQ Group" width="60%"/>
</div>

&nbsp;

The MiroFish team is recruiting full-time/internship positions. If you're interested in multi-agent simulation and LLM applications, feel free to send your resume to: **mirofish@shanda.com**

## 📄 Acknowledgments

**MiroFish has received strategic support and incubation from Shanda Group!**

MiroFish's simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**, We sincerely thank the CAMEL-AI team for their open-source contributions!

## Zhouyi research module

`research/` now targets a fictional human-persona sandbox, not weather. The four chat arms were not run, OASIS is not connected, and this is not a completed MiroFish enhancement experiment. There is no consented behavior record, so it does not show that a chart predicts better. Read [research/README.md](research/README.md).

## 📈 Project Statistics

<a href="https://github.com/666ghj/MiroFish">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="static/image/star-history-dark.svg" />
   <source media="(prefers-color-scheme: light)" srcset="static/image/star-history-light.svg" />
   <img alt="666ghj/MiroFish Star History Chart" src="static/image/star-history-light.svg" />
 </picture>
</a>
