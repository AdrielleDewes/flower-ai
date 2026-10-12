# FlowerAI

**FlowerAI** is an AI-powered bouquet recommendation and customization platform designed to help flower shops offer more personalized shopping experiences.

The project aims to combine traditional e-commerce functionality with AI capabilities, allowing customers to discover flowers, create personalized bouquets, and receive recommendations based on their preferences, occasions, and budgets.

## Key Features

The platform is being developed incrementally, with the following capabilities planned:

- **Bouquet Builder:** Create customized bouquets using available flowers, foliage, and wrapping options.
- **AI-Powered Recommendations:** Interpret natural language requests and suggest bouquets based on customer preferences.
- **Semantic Search:** Find relevant flowers and arrangements beyond exact keyword matching.
- **Image-Based Recommendations:** Upload a reference image and discover similar arrangements using the florist's catalog.
- **Florist Integration:** Provide a solution that flower shops can eventually integrate into their existing websites.

## Technical Approach

FlowerAI follows a modular architecture that separates AI-powered interpretation from deterministic business logic.

Large Language Models (LLMs) are responsible for understanding customer preferences, while the recommendation engine handles catalog availability, inventory constraints, bouquet composition, and pricing.

**Current technologies:** Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, and Ollama.

The project also includes an evaluation framework for comparing language models based on extraction accuracy, hallucination rates, structured output validity, and inference latency.

## Project Status

🚧 **Under active development**

The backend currently includes catalog management, bouquet operations, a rule-based recommendation engine, and an experimental LLM interpretation pipeline.

AI model evaluation and optimization are ongoing. Additional capabilities, including image-based recommendations, frontend development, and florist integrations, are planned for future iterations.

---

*FlowerAI is a personal project exploring practical applications of AI engineering, recommendation systems, and LLM evaluation in e-commerce.*
