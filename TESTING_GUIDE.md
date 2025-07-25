# Frontend Testing Guide

This guide will help you run and test the frontend application with all the implemented features.

## Running the Application

1. Navigate to the project directory:
   ```bash
   cd quantum-leap-frontend
   ```

2. Install dependencies (if not already done):
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to the URL shown in the terminal (typically http://localhost:5173)

## Testing the User Testing Framework

We've implemented a comprehensive user testing framework that includes:

### 1. User Testing Interface

- **Floating Feedback Button**: Look for a floating button in the bottom-right corner of any page
- **Component Selection**: Click on the button and try selecting specific components on the page
- **Feedback Form**: Fill out the feedback form with different types of feedback
- **Error Reporting**: Try reporting bugs or issues you encounter

### 2. Testing Page

Navigate to `/testing` to access the Testing Page which includes:

- **Comprehensive Testing**: Run automated tests for various aspects of the application
- **UI Testing**: Test UI components across different devices and scenarios
  - Test different components
  - View responsive behavior on different device sizes
  - Check test results and reports
- **Accessibility Audit**: Review accessibility compliance
- **Bug Reporting**: Submit detailed bug reports

### 3. Error Reporting Dashboard

Navigate to `/error-reporting` to access the Error Reporting Dashboard which includes:

- **Error Reports**: View and manage user-reported errors
  - Filter by severity and status
  - Update status of error reports
- **User Feedback**: Review feedback submitted by users
  - Filter by type and rating
- **Usability Issues**: Track and prioritize usability issues
- **Analytics**: View metrics on errors, feedback, and usability issues

## Features to Test

1. **User Testing Provider**
   - Test that the context provider correctly manages user testing state
   - Verify that feedback and error reports are stored correctly

2. **Component Selection**
   - Test selecting different components on the page
   - Verify that component information is captured correctly

3. **Feedback Collection**
   - Submit different types of feedback
   - Check that feedback is displayed correctly in the dashboard

4. **Error Reporting**
   - Submit bug reports with different severities
   - Verify that error reports are displayed correctly in the dashboard
   - Test updating the status of error reports

5. **UI Testing**
   - Run UI tests for different components
   - Test responsive behavior on different device sizes
   - Check test results and reports

## Known Limitations

- The application uses localStorage for data storage, so data will be lost if the browser storage is cleared
- Some features may be simulated for demonstration purposes
- Cross-browser testing is limited to the browser you're using

## Feedback

After testing, please provide feedback on:

1. User experience of the testing framework
2. Any bugs or issues encountered
3. Suggestions for improvements
4. Overall usability of the application

Thank you for testing the application!