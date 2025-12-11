# File: features/01_SauceDemo_E2E.feature
Feature: SauceDemo - Complete Purchase Flow as standard_user

  Scenario: TC_SAUCE_001 - End-to-end purchase with 3 items and logout
    Given User navigates to SauceDemo login page "https://www.saucedemo.com"
    When User enters username "standard_user"
    And User enters password "secret_sauce"
    And User clicks the Login button
    Then User is redirected to the inventory page with URL containing "/inventory.html"
    And page title contains "Swag Labs"
    When User selects sorting option "Price (high to low)"
    Then the first product price is "$49.99"
    When User clicks Add to cart on the first item
    And User clicks Add to cart on the second item
    And User clicks Add to cart on the third item
    Then the shopping cart badge displays "3"
    When User clicks the shopping cart icon
    Then the cart page URL contains "cart.html"
    And exactly 3 items are listed in the cart
    When User clicks Checkout button
    Then User is on the checkout step one page
    When User enters First Name "Automation"
    And User enters Last Name "Tester"
    And User enters Zip/Postal Code "11001"
    And User clicks Continue button
    Then User is on checkout overview page
    And Payment Information section shows "SauceCard #31337"
    And Shipping Information shows "Free Pony Express Delivery!"
    And Item total is greater than "$50"
    When User clicks Finish button
    Then checkout complete page shows header "Thank you for your order!"
    And success message contains "Your order has been dispatched"
    When User opens the burger menu
    And User clicks Logout
    Then User is redirected back to login page




# features/06_ParaBank_Banking.feature
Feature: ParaBank - Online Banking with Account Management

  Scenario: TC_PARABANK_001 - User registers, logs in, transfers funds, and logs out
    Given User navigates to ParaBank homepage "https://parabank.parasoft.com/parabank/index.htm"
    When User clicks on Register link
    And User enters First Name "John"
    And User enters Last Name "Doe"
    And User enters Address "123 Main St"
    And User enters City "Springfield"
    And User enters State "IL"
    And User enters Zip Code "62701"
    And User enters Phone "555-1234"
    And User enters SSN "123-45-6789"
    And User enters Username "johndoe"
    And User enters Password "password123"
    And User enters Confirm Password "password123"
    And User clicks Register button
    Then registration success message appears
    When User clicks on Login link
    And User enters Username "johndoe"
    And User enters Password "password123"
    And User clicks Login button
    Then User is on Accounts Overview page
    When User clicks on Transfer Funds link
    And User enters Transfer From Account "12345"
    And User enters Transfer To Account "67890"
    And User enters Amount "100.00"
    And User clicks Transfer button
    Then transfer confirmation message appears
    And balance is updated correctly
    When User clicks on Logout link
    Then User is redirected to homepage
