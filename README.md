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

-- Insert all execution data
INSERT INTO execution (exeid, testcaseid, scripttype, datestamp, exetime, message, output, status) VALUES
('EX0001','TC00011','playwright','2025-11-03','22:25:23','Execution Completed Successfully!','Page title verified: Swag Labs','success'),
('EX0002','TC00011','playwright','2025-11-04','23:41:49.413699','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0003','TC00011','playwright','2025-11-05','00:33:43.079465','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0004','TC00011','playwright','2025-11-05','00:52:43.166151','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0005','TC00011','playwright','2025-11-05','00:54:08.404957','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0006','TC00011','playwright','2025-11-05','00:55:26.640235','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0007','TC00011','playwright','2025-11-05','00:58:20.213804','Script executed successfully','Page title verified: Swag Labs','SUCCESS'),
('EX0008','TC0013','playwright','2025-11-06','12:13:26.341297','Generated script execution','Initializing script execution\nExecuting script...\nRunning action: Navigate to the OrangeHRM login page at 2025-11-06 12:13:17.047247\nAction runned: Navigate to the OrangeHRM login page...\nTC0013: Test Passed - Password reset link was sent successfully.\nExecution completed successfully','SUCCESS'),
('EX0009','TC0013','playwright','2025-11-06','12:14:12.145431','Generated script execution','Initializing script execution\nExecuting script...\n...Execution completed successfully','SUCCESS'),
('EX0010','TC0013','playwright','2025-11-06','12:56:23.395073','Generated script execution','Initializing script execution\nScript file created...\nAction Submit form failed due to timeout\nTest execution completed successfully','SUCCESS'),
('EX0011','TC0013','playwright','2025-11-06','12:57:24.045823','Generated script execution','Initializing script execution\nScript file created...\nTC0013: Test Passed','SUCCESS'),
('EX0012','TC0013','playwright','2025-11-06','12:58:04.04951','Generated script execution','Initializing script execution\n...Test Passed','SUCCESS'),
('EX0013','TC0013','playwright','2025-11-06','13:49:49.401268','Generated script execution','...Test Passed Successfully...','SUCCESS'),
('EX0014','TC0013','playwright','2025-11-06','13:51:34.959276','Generated script execution','...Test Case Passed Successfully','SUCCESS'),
('EX0015','TC0012','playwright','2025-11-07','10:31:31.16051','Generated script execution','Initializing script execution\n...Execution completed successfully','SUCCESS'),
('EX0016','TC0013','playwright','2025-11-07','10:32:38.81551','Generated script execution','...Execution completed successfully','SUCCESS'),
('EX0017','TC0011','playwright','2025-11-15','01:01:46.889681','[AUTO-HEALED] Script executed successfully','Test Case TC0011 Passed!','SUCCESS'),
('EX0018','TC0011','playwright','2025-11-15','01:05:25.49524','[AUTO-HEALED] Script executed successfully','...browser closed...','SUCCESS'),
('EX0019','TC0011','playwright','2025-11-15','01:12:49.618178','[AUTO-HEALED] Script executed successfully','...Test Case Passed...','SUCCESS'),
('EX0020','TC0011','playwright','2025-11-15','01:24:22.269879','[AUTO-HEALED] Script executed successfully','...Test Case TC0011 finished...','SUCCESS'),
('EX0021','TC0011','playwright','2025-11-15','09:52:56.216914','[AUTO-HEALED] Script executed successfully','...Test Case Passed...','SUCCESS'),
('EX0022','TC0012','playwright','2025-11-18','01:35:29.433984','Script exited with code 1','SyntaxError: invalid syntax','FAILED'),
('EX0023','TC0011','playwright','2025-11-18','01:41:58.645208','Script executed successfully','Test Case TC0011 PASSED','SUCCESS'),
('EX0024','TC0011','playwright','2025-11-18','10:20:24.196683','Script executed successfully','Test Case PASSED','SUCCESS'),
('EX0025','TC0013','playwright','2025-11-18','19:42:50.977103','Script executed successfully','Test Case TC0013 PASSED','SUCCESS'),
('EX0026','TC0011','playwright','2025-11-19','11:09:18.250955','Script executed successfully','Test TC0011 PASSED','SUCCESS'),
('EX0027','TC0011','playwright','2025-11-19','11:23:13.193625','Script executed successfully','Test Case TC0011 finished','SUCCESS'),
('EX0028','TC0013','playwright','2025-11-19','11:51:35.905214','Script executed successfully','Test Case Passed','SUCCESS'),
('EX0029','TC0011','playwright','2025-11-19','11:59:56.285777','Script exited with code 1','AssertionError: Page URL expected...','FAILED'),
('EX0030','TC0011','playwright','2025-11-20','02:23:30.570367','Script executed successfully','...Action completed: login...','SUCCESS'),
('EX0031','TC0013','playwright','2025-11-20','02:36:40.78523','Script executed successfully','...Test Completed...','SUCCESS'),
('EX0032','TC0011','playwright','2025-11-20','02:37:54.680943','Script executed successfully','--- Test Execution Finished ---','SUCCESS'),
('EX0033','TC0013','playwright','2025-11-20','02:38:56.353815','Script executed successfully','--- Test Case PASSED ---','SUCCESS'),
('EX0034','TC0011','playwright','2025-11-20','10:10:50.873051','Script exited with code 1','Locator error\nScreenshot saved...','FAILED'),
('EX0035','TC0012','playwright','2025-11-20','10:12:36.61011','Script executed successfully','Test Case TC0012 PASSED','SUCCESS'),
('EX0036','TC0011','playwright','2025-11-20','16:40:31.501707','Script executed successfully','','SUCCESS'),
('EX0037','TC0011','playwright','2025-11-20','16:41:31.43169','Script executed successfully','','SUCCESS'),
('EX0038','TC0011','playwright','2025-11-20','16:57:06.750706','Script executed successfully','...STATUS: PASSED','SUCCESS'),
('EX0039','TC0011','playwright','2025-11-20','17:15:58.088758','Script executed successfully','','SUCCESS'),
('EX0040','TC0011','playwright','2025-11-20','17:18:02.5278','Script executed successfully','','SUCCESS'),
('EX0041','TC0011','playwright','2025-11-20','17:49:47.515726','Script executed successfully','','SUCCESS'),
('EX0042','TC0011','playwright','2025-11-20','17:56:27.762521','Script executed successfully','','SUCCESS'),
('EX0043','TC0012','playwright','2025-11-20','17:57:28.140958','Script executed successfully','','SUCCESS'),
('EX0044','TC0011','playwright','2025-11-20','22:35:36.362247','Script executed successfully','Test Case TC0011 PASSED','SUCCESS'),
('EX0045','TC0011','playwright','2025-11-20','23:23:30.07652','Script executed successfully','--- PASSED ---','SUCCESS'),
('EX0046','TC0011','playwright','2025-11-21','01:01:40.595996','Script exited with code 1','Timeout Error','FAILED'),
('EX0047','TC0011','playwright','2025-11-21','09:19:21.97761','Script executed successfully','Test TC0011 PASSED','SUCCESS'),
('EX0048','TC0009','playwright','2025-11-21','11:29:26.486402','Script executed successfully','Action completed successfully.','SUCCESS'),
('EX0049','TC0012','playwright','2025-11-23','23:32:50.899942','Script executed successfully','Failed at verification','SUCCESS'),
('EX0050','TC0012','playwright','2025-11-23','23:35:20.505898','Script executed successfully','TC0012 FAILED','SUCCESS'),
('EX0051','TC0012','playwright','2025-11-24','00:03:05.539851','Script executed successfully','Test case TC0012 PASSED!','SUCCESS'),
('EX0052','TC0011','playwright','2025-11-24','00:04:11.139465','Script executed successfully','FAILED at dashboard','SUCCESS'),
('EX0053','TC0011','playwright','2025-11-24','00:19:38.230623','Script executed successfully','Test Failed','SUCCESS'),
('EX0054','TC0011','playwright','2025-11-26','08:14:10.122779','Script executed successfully','Test Case PASSED','SUCCESS'),
('EX0055','TC0011','playwright','2025-11-26','08:47:26.913962','Script executed successfully','Dashboard verified successfully','SUCCESS'),
('EX0056','TC0013','playwright','2025-11-26','09:19:30.672435','Script executed successfully','Password reset verified','SUCCESS'),
('EX0057','TC0011','playwright','2025-11-26','16:02:09.283217','Script executed successfully','Test Completed','SUCCESS');


---------------------------------------------


INSERT OR REPLACE INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid, created_on, updated_on, status, no_steps, last_exe_status)
VALUES
('TC0002','DASHBOARD','TC0001','LOGIN','["TAG3"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0003','demo 4','TC0001','login','["tag4"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0009','Verify a user with valid credentials can log in successfully.',NULL,'User should exist in the system.','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0010','Verify the system shows an error for invalid login credentials.',NULL,NULL,'["Login","Negative"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC00011','Verify a user can initiate the password reset process.','TC001',NULL,'["Login"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC004200','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC004200','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0002"]',NULL,NULL,NULL,NULL,NULL),
('TC0020','Verify user can login with valid credentials',NULL,'User must have valid credentials','["Login","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0021','Verify error is shown for invalid login','',NULL,'["Login","Negative"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0022','Verify user can add item to cart','TC0020','User must be logged in','["Cart","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0023','Verify user can remove item from cart','TC0022','User must have item in cart','["Cart"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0024','Verify user can logout successfully','TC0020','User must be logged in','["Login","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0097','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0098','Verify Invalid Login',NULL,NULL,'["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0011','Verify a user with valid credentials can log in successfully.','','User should exist in the system.','["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0097','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0001','login','\n','', '["tag1"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','',NULL,NULL,'[]','["PJ0003"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0013','Verify a user can initiate the password reset process.','TC0011','','["Login"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0012','Verify the system shows an error for invalid login credentials.','', '', '["Login","Negative"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','',NULL,NULL,'[]','["PJ0003"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0071','User Login Test','TC0030','System Ready','["Login","Smoke"]','["PJ0014"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0013"]',NULL,NULL,NULL,NULL,NULL),
('TC0042','Verify Valid Login',NULL,NULL,'["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL);


-------------------------------------------------------------------

INSERT OR REPLACE INTO testcase (testcaseid, testdesc, pretestid, prereq, tag, projectid, created_on, updated_on, status, no_steps, last_exe_status)
VALUES
('TC0002','DASHBOARD','TC0001','LOGIN','["TAG3"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0003','demo 4','TC0001','login','["tag4"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0009','Verify a user with valid credentials can log in successfully.',NULL,'User should exist in the system.','["Login","Smoke"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL),
('TC0010','Verify the system shows an error for invalid login credentials.',NULL,NULL,'["Login","Negative"]','["PJ0001"]',NULL,NULL,NULL,NULL,NULL);
