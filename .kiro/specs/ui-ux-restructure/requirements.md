# UI/UX Restructure Requirements

## Introduction

This specification addresses the critical UI/UX restructuring needed to properly organize AI features according to user expectations and backend capabilities. The current structure incorrectly places AI settings in the AI tools page and lacks portfolio AI integration in the portfolio page itself.

## Requirements

### Requirement 1: Move AI Settings to Main Settings Page

**User Story:** As a user, I want to configure my AI providers in the main Settings page, so that I can find configuration options where I expect them to be.

#### Acceptance Criteria

1. WHEN I navigate to the Settings page THEN I SHALL see an "AI Configuration" section
2. WHEN I click on "AI Configuration" THEN I SHALL see all AI provider settings (OpenAI, Claude, Gemini)
3. WHEN I configure AI settings THEN the system SHALL save my preferences and validate API keys
4. WHEN I save AI settings THEN I SHALL receive confirmation of successful configuration
5. IF I have invalid API keys THEN the system SHALL show clear error messages with guidance

### Requirement 2: Remove AI Settings from AI Tools Page

**User Story:** As a user, I want the AI page to focus on AI tools and features, so that I can access AI functionality without configuration clutter.

#### Acceptance Criteria

1. WHEN I navigate to the AI page THEN I SHALL NOT see AI settings or configuration options
2. WHEN I access the AI page THEN I SHALL see only AI tools and features
3. WHEN I need to configure AI THEN the system SHALL direct me to the Settings page
4. IF my AI is not configured THEN I SHALL see a clear link to Settings page configuration

### Requirement 3: Add Portfolio AI Analysis to Portfolio Page

**User Story:** As a user, I want to analyze my portfolio with AI directly from the portfolio page, so that I can get insights about my investments in context.

#### Acceptance Criteria

1. WHEN I view my portfolio THEN I SHALL see an "AI Analysis" tab or section
2. WHEN I click "AI Analysis" THEN I SHALL see portfolio health score, risk analysis, and recommendations
3. WHEN I trigger portfolio analysis THEN the system SHALL use the backend portfolio co-pilot service
4. WHEN analysis completes THEN I SHALL see diversification metrics, rebalancing suggestions, and trading signals
5. IF I haven't configured AI THEN I SHALL see sample data with clear setup instructions

### Requirement 4: Integrate Portfolio AI with Portfolio Data

**User Story:** As a user, I want portfolio AI analysis to use my actual portfolio data, so that I get personalized insights and recommendations.

#### Acceptance Criteria

1. WHEN portfolio AI analysis runs THEN it SHALL use my current holdings and positions data
2. WHEN I have portfolio data THEN the AI analysis SHALL calculate real health scores and risk metrics
3. WHEN analysis generates recommendations THEN they SHALL be specific to my actual holdings
4. WHEN I view AI insights THEN they SHALL reflect my portfolio's sector allocation and concentration
5. IF my portfolio data changes THEN the AI analysis SHALL update accordingly

### Requirement 5: Maintain AI Tools Functionality

**User Story:** As a user, I want to continue accessing AI tools like strategy generation and market analysis, so that I can use AI features for trading decisions.

#### Acceptance Criteria

1. WHEN I access the AI page THEN I SHALL see all AI tools (Strategy Generation, Market Analysis, Trading Signals, etc.)
2. WHEN I use AI tools THEN they SHALL function with my configured AI providers
3. WHEN AI tools generate results THEN they SHALL be properly formatted and actionable
4. WHEN I haven't configured AI THEN tools SHALL show sample data with setup guidance
5. IF AI tools fail THEN I SHALL see clear error messages and troubleshooting steps

### Requirement 6: Ensure Consistent AI Configuration Access

**User Story:** As a user, I want consistent access to AI configuration from any AI feature, so that I can easily set up AI when needed.

#### Acceptance Criteria

1. WHEN I encounter unconfigured AI features THEN I SHALL see a clear "Configure AI" button
2. WHEN I click "Configure AI" THEN I SHALL be directed to the Settings page AI section
3. WHEN I complete AI configuration THEN I SHALL be able to return to the original feature
4. WHEN AI configuration is complete THEN all AI features SHALL automatically detect the new settings
5. IF AI configuration fails THEN I SHALL see specific error messages and retry options

### Requirement 7: Preserve Existing AI Service Integration

**User Story:** As a user, I want all existing AI functionality to continue working after the restructure, so that I don't lose any features.

#### Acceptance Criteria

1. WHEN the restructure is complete THEN all existing AI API calls SHALL continue to work
2. WHEN I use AI features THEN they SHALL connect to the same backend services
3. WHEN AI providers are configured THEN they SHALL work across all AI features
4. WHEN I switch between AI features THEN my configuration SHALL persist
5. IF any AI feature breaks THEN the system SHALL provide fallback functionality

### Requirement 8: Improve AI Feature Discoverability

**User Story:** As a user, I want to easily discover and access AI features, so that I can take full advantage of the AI capabilities.

#### Acceptance Criteria

1. WHEN I view the portfolio THEN I SHALL clearly see AI analysis options
2. WHEN I access Settings THEN I SHALL easily find AI configuration
3. WHEN I visit the AI page THEN I SHALL see all available AI tools organized clearly
4. WHEN AI features are available THEN they SHALL be prominently displayed
5. IF I'm new to AI features THEN I SHALL see helpful onboarding guidance