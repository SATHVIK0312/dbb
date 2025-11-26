# dbb

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0001', 'testing 1', '2025-10-06', 'API', 'checking demo 1');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0002', 'testing 2', '2025-10-01', 'Frontend', 'demo 2');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0003', 'testing 3', '2026-03-19', 'API', 'demo 3');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0004', 'testing 4', '2025-10-30', 'API', 'demo 4');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0009', 'My First Project', '2025-11-04', 'Automation', 'Created via WPF');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0010', 'demo 11', '2025-11-04', 'API', 'testing pranav software');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0011', 'final demo 1', '2026-01-20', 'API', 'Description sample');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0012', 'sathvik demo', '2026-12-23', 'Frontend', 'demo1');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0013', 'executor', '2025-11-01', 'Automation', 'test cases');

INSERT INTO project (projectid, title, startdate, projecttype, description) VALUES
('PJ0014', 'Sauce Demo', '2025-11-05', 'Frontend', 'Testcases');



--

CREATE TABLE projectuser (
    userid TEXT PRIMARY KEY,
    projectid TEXT
);
INSERT INTO projectuser (userid, projectid) VALUES
('a1', '["PJ0001", "PJ0002"]');

INSERT INTO projectuser (userid, projectid) VALUES
('a2', '["PJ0003"]');

INSERT INTO projectuser (userid, projectid) VALUES
('a3', '["PJ0001", "PJ0002", "PJ0003"]');



CREATE TABLE testcase (
    testcaseid TEXT PRIMARY KEY,
    testdesc TEXT,
    pretestid TEXT,
    prereq TEXT,
    tag TEXT,
    projectid TEXT
);

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0001', 'login', NULL, NULL, '["tag1"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC00011', 'Verify a user can initiate the password reset process.', 'TC001', NULL, '["Login"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0002', 'DASHBOARD', 'TC0001', 'LOGIN', '["TAG3"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0003', 'demo 4', 'TC0001', 'login', '["tag4"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0009', 'Verify a user with valid credentials can log in successfully.', NULL, 'User should exist in the system.', '["Login","Smoke"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0010', 'Verify the system shows an error for invalid login credentials.', NULL, NULL, '["Login","Negative"]', '["PJ0001"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0011', 'Verify a user with valid credentials can log in successfully.', NULL, 'User should exist in the system.', '["Login","Smoke"]', '["PJ0013"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0012', 'Verify the system shows an error for invalid login credentials.', NULL, NULL, '["Login","Negative"]', '["PJ0013"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0013', 'Verify a user can initiate the password reset process.', 'TC0011', NULL, '["Login"]', '["PJ0013"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0020', 'Verify user can login with valid credentials', NULL, 'User must have valid credentials', '["Login","Smoke"]', '["PJ0014"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0021', 'Verify error is shown for invalid login', NULL, NULL, '["Login","Negative"]', '["PJ0014"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0022', 'Verify user can add item to cart', 'TC0020', 'User must be logged in', '["Cart","Smoke"]', '["PJ0014"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0023', 'Verify user can remove item from cart', 'TC0022', 'User must have item in cart', '["Cart"]', '["PJ0014"]');

INSERT INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid) VALUES
('TC0024', 'Verify user can logout successfully', 'TC0020', 'User must be logged in', '["Login","Smoke"]', '["PJ0014"]');


CREATE TABLE teststep (
    testcaseid TEXT PRIMARY KEY,
    steps TEXT,
    args TEXT,
    stepnum INTEGER
);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0001',
 '["STEP1","STEP2","STEP3"]',
 '["NULL","ABC","NULL"]',
 3);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC00011',
 '["Given the user is on the OrangeHRM login page","When the user clicks on \"Forgot your Password?\"","And enters their username","And clicks the \"Reset Password\" button","Then a password reset link should be sent successfully"]',
 '["","","Admin","",""]',
 5);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0009',
 '["Given the user is on the OrangeHRM login page","When the user enters the username","And the user enters the password","And clicks the login button","Then the user should be redirected to the dashboard"]',
 '["https://opensource-demo.orangehrmlive.com/web/index.php/auth/login","Admin","admin123","",""]',
 5);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0010',
 '["Given the user is on the OrangeHRM login page","When the user enters an invalid username","And clicks the login button","Then an \"Invalid credentials\" error message should be displayed"]',
 '["https://opensource-demo.orangehrmlive.com/web/index.php/auth/login","Admin111111","",""]',
 4);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0011',
 '["Given the user is on the OrangeHRM login page","When the user enters the username","And the user enters the password","And clicks the login button","Then the user should be redirected to the dashboard"]',
 '["https://opensource-demo.orangehrmlive.com/web/index.php/auth/login","Admin","admin123","",""]',
 5);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0012',
 '["Given the user is on the OrangeHRM login page","When the user enters an invalid username","And clicks the login button","Then an \'Invalid credentials\' error message should be displayed"]',
 '["https://opensource-demo.orangehrmlive.com/web/index.php/auth/login","Admin111111","",""]',
 4);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0013',
 '["Given the user is on the OrangeHRM login page","When the user clicks on \'Forgot your Password?\'","And enters their username","And clicks the \'Reset Password\' button","Then a password reset link should be sent successfully"]',
 '["https://opensource-demo.orangehrmlive.com/web/index.php/auth/login","","Admin","",""]',
 5);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0020',
 '["Given the user is on SauceDemo login page","When the user logs in with username and password","Then the user should be redirected to the Products page"]',
 '["https://www.saucedemo.com","standard_user","secret_sauce"]',
 3);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0021',
 '["Given the user is on SauceDemo login page","When the user enters invalid username and password","Then an error message should be displayed"]',
 '["https://www.saucedemo.com","invalid_user","wrong_pass"]',
 3);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0022',
 '["Given the user is logged into SauceDemo","When the user adds an item to the cart","Then the item should be visible in the cart"]',
 '["https://www.saucedemo.com","Sauce Labs Backpack","1"]',
 3);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0023',
 '["Given the user has an item in cart","When the user removes the item from the cart","Then the cart should be empty"]',
 '["https://www.saucedemo.com","SauceLabs Backpack",""]',
 3);

INSERT INTO teststep (testcaseid, steps, args, stepnum) VALUES
('TC0024',
 '["Given the user is logged into SauceDemo","When the user logs out","Then the user should be redirected to login page"]',
 '["https://www.saucedemo.com","",""]',
 3);


------

CREATE TABLE user (
    mail TEXT PRIMARY KEY,
    password TEXT,
    userid TEXT,
    role TEXT,
    name TEXT
);
INSERT INTO user (mail, password, userid, role, name) VALUES
('chetanw@gmail.com', 'chetanedc', 'a2', 'role-1', 'mokshit');

INSERT INTO user (mail, password, userid, role, name) VALUES
('xyz@gmail.com', 'Xyz@123', 'b1', 'role-2', 'chetan');

INSERT INTO user (mail, password, userid, role, name) VALUES
('qw@gmail.com', '123edc', 'b2', 'role-2', 'chetan');

INSERT INTO user (mail, password, userid, role, name) VALUES
('abc@gmail.com', 'Abc@123', 'a1', 'role-1', 'pranav');

INSERT INTO user (mail, password, userid, role, name) VALUES
('mokshshshshsw@gmail.com', 'chetanedc', 'a3', 'role-1', 'pranav');

INSERT INTO user (mail, password, userid, role, name) VALUES
('chase@gmail.com', 'hyderabad', 'b3', 'role-2', 'jpmc');

INSERT INTO user (mail, password, userid, role, name) VALUES
('abc123@email.com', 'abc123', 'b4', 'role-2', 'vedansh');

INSERT INTO user (mail, password, userid, role, name) VALUES
('abs@gmaill.com', 'abc123', 'a4', 'role-1', 'pranav2');

INSERT INTO user (mail, password, userid, role, name) VALUES
('abcdef@gmail.com', 'abc123', 'b5', 'role-2', 'sathvik');

----------------------------------------------------------------------25/11/25

CREATE TABLE IF NOT EXISTS testcase (
    testcaseid TEXT NOT NULL PRIMARY KEY,
    testdesc TEXT,
    pretestid TEXT,
    prereq TEXT,
    tag TEXT,              -- Store array as JSON string
    projectid TEXT,        -- Store array as JSON string
    created_on TEXT,       -- SQLite stores dates as TEXT (ISO format)
    updated_on TEXT,
    status TEXT,
    no_steps INTEGER,
    last_exe_status TEXT
);

INSERT INTO testcase (
    testcaseid, testdesc, pretestid, prereq, tag, projectid, 
    created_on, updated_on, status, no_steps, last_exe_status
) VALUES (
    'TC9999',
    'Random sample test description',
    'TC0001',
    'System ready',
    '["Login", "Smoke"]',
    '["PJ1234"]',
    '2025-02-05 10:30:00',
    '2025-02-05 11:00:00',
    'Pending',
    4,
    'Not Executed'
);


----------------------------------------------
CREATE TABLE execution (
    exeid TEXT PRIMARY KEY,
    testcaseid TEXT,
    scripttype TEXT,
    datestamp TEXT DEFAULT (DATE('now')),
    exetime TEXT DEFAULT (TIME('now')),
    message TEXT,
    output TEXT,
    status TEXT
);
