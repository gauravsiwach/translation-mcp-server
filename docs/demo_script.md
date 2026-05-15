 # 3-minute Demo Script — Translation MCP Server

Purpose: A concise, speaker-ready 3-minute demo script to present the project, show core flows, and offer a demo CTA.

Timeline & Script

0:00 – 0:05 | Welcome

“Hi, today I’ll demonstrate how an AI-enabled MCP pipeline simplifies translation generation.”

0:05 – 0:35 | Intro + Problem

“Let me start with the core problem we are trying to solve.

Localization is a critical part of any global application — but at scale, it becomes a major operational challenge.

If we look at the PepsiCo B2B portal, it already supports more than 15 markets — and this number is continuously growing.

Now, every new feature introduces new translation keys — and each key needs to be translated, reviewed, versioned, and promoted across multiple environments.

And this is where the real problem begins.

Today, this entire process is largely manual. Teams rely on tools like Google Translate, which don’t understand business context, user intent, or market nuances — resulting in inconsistent or sometimes incorrect translations.

But the bigger issue is not just translation — it’s lifecycle management.

When these changes move from DEV to QA to PROD, there’s a high risk of missing keys, duplicating entries, or pushing incorrect translations — which directly impacts user experience.

So what we’re dealing with is not just inefficiency — it’s a system that is error-prone, hard to control, and very difficult to scale.”

0:35 – 1:00 | Solution Overview

“To address these challenges, we’ve built an AI-enabled pipeline. Let me walk you through how it works.

The solution is a Translation MCP Server, where we expose both REST APIs and MCP tools.

This allows users to add or update localization keys either through structured JSON payloads or simply through natural language.

Once a request is triggered, the system runs an AI pipeline that generates the required translations and updates them in the appropriate source for the target market and locales.

So at a high level, we are turning a manual, fragmented process into a unified, AI-powered workflow.”

1:00 – 1:20 | How It Works Internally

“Let me briefly explain how this works behind the scenes.

From an architecture perspective, we are leveraging the existing PostgreSQL database already used in current systems.

On top of that, we have designed services that interact with the database and expose capabilities through REST APIs and MCP tools.

This allows developers or business users to integrate or directly interact using natural language — to add, update, delete, or review translation keys.

We also support a human-in-the-loop workflow, where users can approve or reject translations.

Those decisions are fed back into the AI pipeline, enabling continuous learning and improving future outputs.

And once validated, these translations can be easily promoted across environments.

The AI layer itself is flexible — it can integrate with providers like OpenAI, Anthropic, in-house APIs, Ollama, or enterprise tools like GitHub Copilot — depending on business needs.”

1:20 – 2:00 | Demo 1 – Add Translation

We have already integrated our MCP server with the IDE, in this case using Windsurf.
“Now let’s look at this in action with a simple example.

I’ll start by simply saying ‘Hi’ to the agent.

The agent responds by asking which mode I want to use:
API mode — where it uses providers like OpenAI or Anthropic
or Tool mode — which leverages enterprise integrations

Let’s select Tool mode.

Now the agent gives me options like:

listing translations
translating keys
updating, approving, or rejecting translations

I’ll choose to add new keys.

Let’s say I ask: ‘Add labels for basket and price on the basket page.’

Now, based on the context, the system intelligently generates structured translation keys.

It then asks me which market I want — I select the desired market.

After confirmation, the AI pipeline is triggered — translations are generated and automatically saved into the system.”

2:00 – 2:25 | Demo 2 – Smart Key Handling

“Let’s look at another scenario to see how the system handles existing keys.

This time, I’m not aware of existing keys — and I ask the agent again:
‘Add labels for basket and price on the basket page.’

But instead of blindly creating new keys, the system intelligently detects that similar keys already exist.

So it doesn’t duplicate — it prompts me for the next step.

Now I can guide it — for example, I ask it to create new keys with a ‘_1’ postfix.

It generates the updated keys, asks for confirmation, and once approved — the new keys are created exactly as requested.

So instead of duplication or confusion, the system ensures consistency while still giving flexibility.”

2:25 – 2:45 | Human Review

“Now let’s look at how review and validation are handled.

All AI-generated translations are tagged with a status like ‘AI generated’ along with a confidence score.

Now I can simply ask:
‘Show me AI-generated translations for the India market.’

The system lists those entries, and I can review them one by one.

For each key, I can either approve it if it looks correct — or reject it and provide a corrected value.

Once approved, the translation is finalized.
If rejected, the corrected version is saved.

And importantly, these decisions feed back into the AI pipeline — helping improve future translation quality for similar keys, markets, and contexts.”

2:45 – 3:05 | MCP Value + Future Scope

“Finally, let’s look at the overall value and future potential of this solution.

The real power of MCP is in simplifying the entire localization lifecycle.

And there is significant potential to further enhance this solution and add more value-driven features.

For example, we can promote translations from one environment to another — like DEV to QA or PROD — in a controlled and reliable way, without missing keys, and with the ability to roll back if needed.

This solution also has strong potential to evolve further and unlock even more value across the organization.

Today, the MCP tools are integrated with PostgreSQL, but the design is extensible — we can add wrappers to support other databases or systems.

On the AI side, we are already leveraging existing enterprise subscriptions, and we can easily extend this with additional AI providers.

We can also enrich this further by integrating design context — for example from tools like Figma — so business users get better visibility into where and how a translation is used.

So this is not just a tool — it’s a scalable foundation for enterprise-wide localization.”