# AI Integration Cleanup Requirements

## Introduction

The current AI integration has multiple issues that create user confusion and poor experience:
1. Multiple tabs/pages that don't have working backend endpoints
2. CORS errors preventing API calls
3. Inconsistent UI/UX across AI features
4. API key storage works but isn't properly linked to settings display
5. Non-functional features misleading users

This spec aims to clean up the AI frontend to provide a consistent, working experience with only functional features.

## Requirements

### Requirement 1: Remove Non-Functional AI Features

**User Story:** As a user, I want to see only working AI features so that I'm not confused by broken functionality.

#### Acceptance Criteria
1. WHEN I access the AI page THEN I should only see tabs/features that have working backend endpoints
2. WHEN I interact with any AI feature THEN it should either work properly or show a clear "coming soon" message
3. WHEN I navigate through AI features THEN there should be no broken links or error states
4. IF a feature is not implemented THEN it should be hidden from the UI entirely

### Requirement 2: Fix API Key Settings Integration

**User Story:** As a user, I want my saved API keys to be properly reflected in the settings interface so that I can manage my AI configuration effectively.

#### Acceptance Criteria
1. WHEN I save an API key THEN it should be properly stored and encrypted
2. WHEN I return to AI settings THEN my saved keys should show as configured (masked)
3. WHEN I update my AI provider preference THEN it should be saved and reflected in the UI
4. WHEN I validate an API key THEN the validation should work without CORS errors

### Requirement 3: Resolve CORS and API Connection Issues

**User Story:** As a user, I want AI features to work without connection errors so that I can use the functionality reliably.

#### Acceptance Criteria
1. WHEN I make API calls to AI endpoints THEN they should not fail with CORS errors
2. WHEN the backend endpoint doesn't exist THEN the frontend should handle it gracefully
3. WHEN there are connection issues THEN users should see helpful error messages
4. WHEN API calls fail THEN there should be proper retry mechanisms

### Requirement 4: Streamline AI Page Structure

**User Story:** As a user, I want a clean, focused AI interface that shows only what works so that I can efficiently use AI features.

#### Acceptance Criteria
1. WHEN I access the AI page THEN I should see a maximum of 3-4 working tabs
2. WHEN I use AI features THEN the UI should be consistent in colors, fonts, and layout
3. WHEN I navigate between AI features THEN the experience should be smooth and predictable
4. WHEN features are loading THEN there should be consistent loading states

### Requirement 5: Implement Working Core AI Features

**User Story:** As a user, I want at least basic AI functionality to work properly so that I can benefit from AI assistance.

#### Acceptance Criteria
1. WHEN I configure API keys THEN the settings should save and load properly
2. WHEN I have valid API keys THEN I should be able to use basic AI chat functionality
3. WHEN I check AI status THEN it should accurately reflect my configuration
4. WHEN I use AI features THEN they should provide value or clear feedback

### Requirement 6: Consistent Error Handling and User Feedback

**User Story:** As a user, I want clear feedback when things go wrong so that I know how to fix issues.

#### Acceptance Criteria
1. WHEN API calls fail THEN I should see user-friendly error messages
2. WHEN features are not available THEN I should see clear "coming soon" or setup messages
3. WHEN I need to configure something THEN I should get clear guidance
4. WHEN errors occur THEN they should not crash the entire interface

## Priority Features to Keep

### High Priority (Must Work)
1. **AI Settings/Configuration** - API key management
2. **AI Status Widget** - Show provider status
3. **Basic AI Chat** - Simple OpenAI integration (if backend supports)

### Medium Priority (If Backend Supports)
1. **Portfolio AI Analysis** - Basic portfolio insights
2. **Strategy Suggestions** - Simple AI recommendations

### Low Priority (Remove if Not Working)
1. **Market Analysis** - Complex market AI features
2. **Crowd Intelligence** - Community AI features
3. **Advanced Analytics** - Complex AI analytics
4. **Strategy Clustering** - Advanced AI clustering

## Technical Requirements

### Backend Endpoint Verification
1. Identify which `/api/ai/*` endpoints actually exist and work
2. Remove frontend calls to non-existent endpoints
3. Add proper error handling for missing endpoints

### CORS Resolution
1. Fix CORS issues for existing AI endpoints
2. Add proper error handling for connection failures
3. Implement retry logic for failed requests

### UI/UX Consistency
1. Use consistent color scheme across all AI features
2. Standardize loading states and error messages
3. Ensure responsive design works properly
4. Remove duplicate or conflicting UI elements

## Success Criteria

### User Experience
- Users can configure AI settings without errors
- Only working features are visible and accessible
- Error messages are helpful and actionable
- UI is consistent and professional

### Technical Quality
- No CORS errors in console
- No broken API calls
- Proper error boundaries and handling
- Clean, maintainable code structure

### Functionality
- API key management works end-to-end
- At least one AI feature provides real value
- Status indicators are accurate
- Settings persist properly

## Out of Scope

- Implementing new AI features
- Complex AI model integrations
- Advanced AI analytics
- Real-time AI streaming (unless already working)
- Multi-model AI orchestration

## Acceptance Testing

### Manual Testing Scenarios
1. **Settings Flow**: Configure API key → Save → Reload page → Verify settings persist
2. **Error Handling**: Try invalid API key → Verify helpful error message
3. **Feature Access**: Navigate through all AI tabs → Verify no broken features
4. **Status Display**: Check AI status widget → Verify accurate status
5. **Responsive Design**: Test on mobile/tablet → Verify UI works properly

### Automated Testing
1. API endpoint availability tests
2. Settings persistence tests
3. Error handling tests
4. UI component rendering tests