# Specter browser-preview fork end-to-end test (2026-10-08)

This documentation-only change exists to produce a unique source commit for
testing the Specter DIY web preview pipeline. It does not change firmware,
simulator functionality, security policy, or CI configuration.

Expected test behavior:
- Build preview from this exact commit.
- Verify the resulting browser preview and firmware artifact.
- Post one compact Specter PR Build comment by specter-preview-bot.
- Never modify any PR outside the schnuartz-ai fork.

DO NOT MERGE this test pull request.

Footer E2E assertion: Under-device firmware provenance footer shows the
firmware version and short source SHA, separated by a middle dot, and links
to that exact source commit. The bot must PATCH its existing comment.

E2E retest on 2026-10-08 after preview-route isolation, fork repository validation, and reporting guard updates.
