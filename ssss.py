# File: features/01_SauceDemo_E2E.feature
Feature: SauceDemo - Complete Purchase Flow as standard_user

  Scenario: TC_SAUCE_001 - End-to-end purchase with 3 items and logout
    Given I navigate to SauceDemo login page "https://www.saucedemo.com"
    When I enter username "standard_user"
    And I enter password "secret_sauce"
    And I click the Login button
    Then I am redirected to the inventory page with URL containing "/inventory.html"
    And page title contains "Swag Labs"
    When I select sorting option "Price (high to low)"
    Then the first product price is "$49.99"
    When I click Add to cart on the first item
    And I click Add to cart on the second item
    And I click Add to cart on the third item
    Then the shopping cart badge displays "3"
    When I click the shopping cart icon
    Then the cart page URL contains "cart.html"
    And exactly 3 items are listed in the cart
    When I click Checkout button
    Then I am on the checkout step one page
    When I enter First Name "Automation"
    And I enter Last Name "Tester"
    And I enter Zip/Postal Code "11001"
    And I click Continue button
    Then I am on checkout overview page
    And Payment Information section shows "SauceCard #31337"
    And Shipping Information shows "Free Pony Express Delivery!"
    And Item total is greater than "$50"
    When I click Finish button
    Then checkout complete page shows header "Thank you for your order!"
    And success message contains "Your order has been dispatched"
    When I open the burger menu
    And I click Logout
    Then I am redirected back to login page
