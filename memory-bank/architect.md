# Academic Figures MCP: System Architect

## Overview

This file captures the current architectural direction for the Academic Figures MCP product surface.

## Current Architectural Direction

1. Single public render tool.

   New bitmap creation should converge on one generic generation tool. The renderer should consume a generic render-ready payload rather than a PMID-bound request so the same contract can later support figures, icons, and adjacent visual assets.

2. Harness-first orchestration.

   Planning, evaluation, preset resolution, revision loops, batch execution, and workflow-state enforcement belong to harness tools around the renderer. Those tools provide product differentiation without fragmenting the actual image-creation contract.

3. Domain intake stays upstream.

   PMID, journal guidance, citation rules, and style intent are valuable domain inputs, but they should be transformed into a reusable planned payload before crossing the generation boundary.
