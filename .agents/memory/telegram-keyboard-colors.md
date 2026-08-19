---
name: Telegram keyboard colors
description: Native Telegram bot keyboards do not expose per-button background colors.
---

Native `ReplyKeyboardMarkup` and `InlineKeyboardMarkup` buttons inherit the Telegram client's theme; Bot API code cannot assign separate green, purple, or red button backgrounds. Matching a screenshot with individually colored buttons requires a Telegram Web App or another rendered surface.

**Why:** The Fantasy Chat request exposed this platform limitation while comparing a native keyboard with a screenshot showing individually colored buttons.

**How to apply:** Preserve native keyboard behavior when that is the requested surface, and explain the limitation before proposing a Web App redesign.