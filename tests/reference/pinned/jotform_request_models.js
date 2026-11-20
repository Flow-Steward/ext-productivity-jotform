var apikeyDescription = "Jotform User API Key <br/> <a target=\"_blank\" href='https://www.jotform.com/myaccount/api'>Get a new API Key</a> ";
var idDescription = "Form ID is the numbers you see on a form URL: https://www.jotformpro.com/form/<b>30693660548966</b>.";
var qidDescription = "Identifier for each question on a form. You can get a list of question IDs from /form/{id}/questions end point.";

var userInfo = {
    id:"user",
    type: "GET",
    url: "/user",
    definition: "Get User Information",
    explanation: "Get user account details for this Jotform user. Including user account type, avatar URL, name, email, website URL.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                 
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userForms = {
    id:"user-forms",
    type: "GET",
    url: "/user/forms",
    definition: "Get User Forms",
    explanation: "Get a list of forms for this account. Includes basic details such as title of the form, when it was created, number of new and total submissions.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "offset",
        description: "Start of each result set for form list. Useful for pagination. Default is 0.",
        example: "20",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false
    },{
        name: "limit",
        description: "Number of results in each result set for form list. Default is 20. Maximum is 1000.",
        example: "30",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false    
    },{
        name: "filter",
        description: "Filters the query results to fetch a specific form range.",
        example: "{\"new\":\"1\"} <br> You can also use gt(greater than), lt(less than), ne(not equal to) commands to get more advanced filtering :<br> Example: {\"created_at:gt\":\"2013-01-01 00:00:00\"}" ,
        type: "jsonString",
        values: ["id", "title","created_at","status","new", "updated_at"],
        inputType: "textarea",
        parameterType:"query",
        required: false
    },{
        name: "orderby",
        description: "Order results by a form field name: id, username, title, status(ENABLED, DISABLED, DELETED), created_at, updated_at, new (unread submissions count), count (all submissions count), slug (used in form URL).",
        example: "created_at",
        type: "Enum",
        values: ["id", "username", "title", "status", "created_at", "updated_at", "new", "count", "slug"],
        inputType: "select",
        parameterType:"query",
        required: false
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userSubmissions = {
    id:"user-submissions",
    type: "GET",
    url: "/user/submissions",
    definition: "Get User Submissions",
    explanation: "Get a list of all submissions for all forms on this account. The <b>answers</b> array has the submission data. Created_at is the date of the submission.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "offset",
        description: "Start of each result set for submission data. Useful for pagination. Default is 0.",
        example: "20",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false
    },{
        name: "limit",
        description: "Number of results in each result set for submission data. Default is 20. Maximum is 1000.",
        example: "30",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false    
    },{
        name: "filter",
        description: "Filters the query results to fetch a specific submissions range.",
        example: "{\"new\":\"1\"} <br> You can also use gt(greater than), lt(less than), ne(not equal to), formIDs and fullText commands to get more advanced filtering :<br> Example: {\"created_at:gt\":\"2013-01-01 00:00:00\"}<br> Example: {\"formIDs\":[\"your-form-id\",\"your-form-id#2\"]}<br> Example: {\"fullText\":\"John Brown\"}" ,
        type: "jsonString",
        values: ["id", "form_id", "IP","created_at","status","new","flag", "updated_at"],
        inputType: "textarea",
        parameterType:"query",
        required: false
    },{
        name: "orderby",
        description: "Order results by a submission field name: id, form_id, IP, created_at, status, new, flag, updated_at.",
        example: "created_at",
        type: "Enum",
        values: ["id", "form_id", "IP","created_at","status","new","flag", "updated_at"],
        inputType: "select",
        parameterType:"query",
        required: false
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userFolders = {
    id:"user-folders",
    type: "GET",
    url: "/user/folders",
    definition: "Get User Folders",
    explanation: "Get a list of form folders for this account. Returns name of the folder and owner of the folder for shared folders. (<b>IMPORTANT: This endpoint is deprecated. Refer to the 'label' endpoints section for the updated endpoints.</b>)",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userHistory = {
    id:"user-history",
    type: "GET",
    url: "/user/history",
    definition: "Get History",
    explanation: "User activity log about things like forms created/modified/deleted, account logins and other operations.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "action",
        description: "Filter results by activity performed. Default is 'all'. ",
        Example: "userLogin",
        type: "Enum",
        inputType: "select",
        parameterType:"query",
        required: false,
        values: ["all", "userCreation", "userLogin","formCreation","formUpdate","formDelete","formPurge"]

    }, {
        name: "date",
        description: "Limit results by a date range. If you'd like to limit results by specific dates you can use startDate and endDate fields <b>instead</b>.",
        type: "Enum",
        example: "lastWeek",
        inputType: "select",
        parameterType:"query",
        required: false,
        values: ["lastWeek", "lastMonth", "last3Months", "last6Months", "lastYear", "all"] 
    }, {
        name: "sortBy",
        description: "Lists results by ascending and descending order",
        type: "Enum",
        example: "ASC",
        inputType: "select",
        parameterType:"query",
        required: false,
        values: ['ASC', 'DESC']  
    },{
        name: "startDate",
        description: "Limit results to only after a specific date.  Format: MM/DD/YYYY.",
        example: "01/31/2013",
        type: "String",
        inputType: "date",
        parameterType:"query",
        required: false
    },{
        name: "endDate",
        description: "Limit results to only before a specific date. Format: MM/DD/YYYY.",
        example: "12/31/2013",
        type: "String",
        inputType: "date",
        parameterType:"query",
        required: false
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userSettings = {
    id:"user-settings",
    type: "GET",
    url: "/user/settings",
    definition: "Get User Settings",
    explanation: "Get user's time zone and language.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],

};

var userSettingsPOST = {
    id:"post-user-settings",
    type: "POST",
    url: "/user/settings",
    definition: "Update User Settings",
    explanation: "Update user's settings like time zone and language.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                    
    },{
        name: "name",
        description: "User's name",
        example: "John Smith",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "email",
        description: "User's email",
        example: "john@smith.com",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "website",
        description: "User's website",
        example: "www.johnsmith.com",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "time_zone",
        description: "User's time zone",
        example: "UTC",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "company",
        description: "User's company",
        example: "Interlogy, LLC.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "securityQuestion",
        description: "User's security question",
        example: "What was your first car?",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "securityAnswer",
        description: "User's security answer",
        example: "Ford",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false
    },{
        name: "industry",
        description: "User's industry",
        example: "Education",
        type: "String",
        inputType: "select",
        parameterType:"post",
        required: false,
        values: ["Education", "Web Design", "Religious", "Non-Profit", "Event Organizer", "Marketing", "Web Development", "Consultancy", "Photography", "Social Media", "Small Business", "Sports", "Real Estate", "Human Resources", "Other"]
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],

};


var userSubusers = {
    id:"user-subusers",
    type: "GET",
    url: "/user/subusers",
    definition: "Get Sub-User Account List",
    explanation: "Get a list of sub users for this accounts and list of forms and form folders with access privileges. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userUsage = {
    id:"user-usage",
    type: "GET",
    url: "/user/usage",
    definition: "Get Monthly User Usage",
    explanation: "Get number of form submissions received this month. Also, get number of SSL form submissions, payment form submissions and upload space used by user. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};


var userReports = {
    id:"user-reports",
    type: "GET",
    url: "/user/reports",
    definition: "Get User Reports",
    explanation: "List of URLS for reports in this account. Includes reports for all of the forms. ie. Excel, CSV, printable charts, embeddable HTML tables.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};


var userLogin = {
    id:"user-login",
    type: "POST",
    url: "/user/login",
    definition: "Login user with given credentials",
    explanation: "",
    parameters: [{
        name: "username",
        description: "User's username",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "password",
        description: "User's password",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "appName",
        description: "Your application name",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                  
    },{
        name: "access",
        description: "Full access able to do write operations, but readOnly just for reading operations",
        type: "String",
        inputType: "select",
        parameterType:"post",
        required: false,  
        values: ['readOnly', 'full']
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userLogout = {
    id:"user-logout",
    type: "GET",
    url: "/user/logout",
    definition: "Logout user",
    explanation: "",
    parameters: [{
        name: "No parameter needed",
        type: "",
        inputType: "",
        parameterType:"",
        required: true
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formId = {
    id:"form-id",
    type: "GET",
    url: "/form/{id}",
    definition: "Get Form Details",
    explanation: "Get basic information about a form. Use /form/{id}/questions to get the list of questions.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query"  ,
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                 
    },{
        name: "id",
        description: idDescription,
        type: "String",
        example: "30693660548966",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};
var formIdFiles = {
    id:"form-id-files",
    type: "GET",
    url: "/form/{id}/files",
    definition: "Get Form Uploads",
    explanation: "List of files uploaded on a form. Here is how you can access a particular file: https://www.jotform.com/uploads/{username}/{form-id}/{submission-id}/{file-name}. Size and file type is also included.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdQuestions = {
    id:"form-id-questions",
    type: "GET",
    url: "/form/{id}/questions",
    definition: "Get Form Questions",
    explanation: "Get a list of all questions on a form. Type describes <a href='https://www.jotform.com/help/46-quick-overview-of-form-fields/'>question field type</a>. Order is the question order in the form. Text field is the question label.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdProperties = {
    id:"form-id-properties",
    type: "GET",
    url: "/form/{id}/properties",
    definition: "Get Form Properties",
    explanation: "Get a list of all <a href='properties/' target='_blank'>properties</a> on a form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdPropertiesProperty = {
    id:"form-id-properties-key",
    type: "GET",
    url: "/form/{id}/properties/{key}",
    definition: "Get a Form Property",
    explanation: "Get a specific <a href='properties/?field=form' target='_blank'>property</a> of the form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "key",
        description: "Property key<br>You can find property descriptions at <a href='properties/?field=form' target='_blank'>property list</a> of the form.",
        type: "String",
        inputType: "select",
        parameterType:"url",
        required: true,
        replace: "{key}",
        values: ["fontsize", "options", "hideMailEmptyFields", "limitSubmission", "messageOfLimitedForm", "sendpostdata", "activeRedirect", "alignment", "expireDate", "font", "fontcolor", "formWidth", "highlightLine", "labelWidth", "lineSpacing", "pagetitle", "styles", "thanktext", "unique", "uniqueField", "background", "secure", "expiredDate", "injectCSS", "disabled", "thankurl"]                 
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdReports = {
    id:"form-id-reports",
    type: "GET",
    url: "/form/{id}/reports",
    definition: "Get form reports",
    explanation: "Get all the reports of a specific form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdReportsPOST = {
    id:"post-form-id-reports",
    type: "POST",
    url: "/form/{id}/reports",
    definition: "Create report",
    explanation: "Create new report of a form with intended fields, type and title.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "title",
        description: "Report title",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true                
    },{
        name: "list_type",
        description: "Report type",
        type: "String",
        inputType: "select",
        parameterType:"post",
        required: true,
        values: ["csv", "excel", "grid", "table", "rss"]
    },{
        name: "fields",
        description: "Report fields.<br>User IP, submission date (dt) and question IDs.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdSubmissions = {
    id:"form-id-submissions",
    type: "GET",
    url: "/form/{id}/submissions",
    definition: "Get Form Submissions",
    explanation: "List of form responses. <b>answers</b> array has the submitted data. Created_at is the date of the submission.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                  
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "offset",
        description: "Start of each result set for form list. Useful for pagination. Default is 0.",
        example: "20",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false
    },{
        name: "limit",
        description: "Number of results in each result set for form list. Default is 20. Maximum is 1000.",
        example: "30",
        type: "Number",
        inputType: "text",
        parameterType:"query",
        required: false    
    },{
        name: "filter",
        description: "Filters the query results to fetch a specific submissions range.",
        example: "{\"id:gt\":\"31974353596870\"} <br> You can also use gt(greater than), lt(less than), ne(not equal to) commands to get more advanced filtering :<br> Example: {\"created_at:gt\":\"2013-01-01 00:00:00\"}<br> Example: {\"workflowStatus:ne\":\"Approve\"}" ,
        type: "jsonString",
        values: ["id", "form_id", "IP", "created_at", "status", "new", "flag", "updated_at", "workflowStatus"],
        inputType: "textarea",
        parameterType:"query",
        required: false
    },{
        name: "orderby",
        description: "Order results by a form field name: id, username, title, status(ENABLED, DISABLED, DELETED), created_at, updated_at, new (unread submissions count), count (all submissions count), slug (used in form URL).",
        example: "created_at",
        type: "Enum",
        values: ["id", "username", "title", "status", "created_at", "updated_at", "new", "count", "slug"],
        inputType: "select",
        parameterType:"query",
        required: false
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdSubmissionsPOST = {
    id:"post-form-id-submissions",
    type: "POST",
    url: "/form/{id}/submissions",
    definition: "Add a Submission to the Form",
    explanation: "Submit data to this form using the API. You should get a list of question IDs from form/{id}/questions and send the submission data with qid.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "submission[1]",
        description: "Data entered in question 1. You should first get a list of question IDs from form/{id}/questions. Or, look at the source code of the form.",
        example: "john@example.com",
        type: "String",
        inputType: "text",
        parameterType: "post",
        required: true
    },{
        name: "submission[2][first]",
        description: "Data entered in question 2. In this example the second question is a full name question. So, there are two fields in this question: firstName and lastName. These fields can be found by looking at the source code of the form.",
        example: "John",
        type: "String",
        inputType: "text",
        parameterType: "post",
        required: false
    },{
        name: "submission[2][last]",
        description: "Data entered in the second part of question 2.",
        example: "Smith",
        type: "String",
        inputType: "text",
        parameterType: "post",
        required: false
    },{
        name: "submission[3]",
        description: "Data entered in question 3. (You should get a list of question IDs from form/{id}/questions)",
        example: "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        type: "String",
        inputType: "text",
        parameterType: "post",
        required: false
    }],
    statusCodes: [{
        code: 400,
        reason: "Question ID is not in request"
    }],
};

var formIdSubmissionsPUT = {
    id:"put-form-id-submissions",
    type: "PUT",
    url: "/form/{id}/submissions",
    definition: "Add Submissions to the Form",
    explanation: "Submit data to this form using the API. You should get a list of question IDs from form/{id}/questions and send the submission data with qid.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "submission",
        description: "Submission data with question IDs.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true                
    }],
    statusCodes: [{
        code: 400,
        reason: "Question ID is not in request"
    }],
};

var formIdQuestionQid = {
    id:"form-id-question-id",
    type: "GET",
    url: "/form/{id}/question/{qid}",
    definition: "Get Details About a Question",
    explanation: "Form questions might have various <a href='properties/' target='_blank'>properties</a>. Examples: Is it required? Are there any validations such as 'numeric only'? ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }, {
        name: "qid",
        description: qidDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{qid}"          
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var reportID = {
    id:"report-id",
    type: "GET",
    url: "/report/{id}",
    definition: "Get Report Details",
    explanation: "Get more information about a data report.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Report ID. You can get a list of reports from /user/reports. For example, you can see the report ID in this report URL: https://www.jotform.com/rss/<b>31753290421044</b>",
        example: "31753290421044",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var deleteReport = {
    id:"delete-report-id",
    type: "DELETE",
    url: "/report/{id}",
    definition: "Delete a Report",
    explanation: "Delete an existing report.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "id",
        description: "Report ID. You can get a list of reports from /user/reports. For example, you can see the report ID in this report URL: https://www.jotform.com/rss/<b>31753290421044</b>",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};


var submissionID = {
    id:"submission-id",
    type: "GET",
    url: "/submission/{id}",
    definition: "Get Submission Data",
    explanation: "Similar to /form/{form-id}/submissions. But only get a single submission. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Submission ID. You can get submission IDs when you call /form/{id}/submissions. View submissions directly on a browser: https://www.jotform.com/submission/<b>235194815571509962</b>.",
        example: "235194815571509962",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};


var formWebHooks = {
    id:"form-id-webhooks",
    type: "GET",
    url: "/form/{id}/webhooks",
    definition: "List of Webhooks for a Form",
    explanation: "Webhooks can be used to send form submission data as an instant notification. Returns list of webhooks for this form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formWebHooksPOST = {
    id:"post-form-id-webhooks",
    type: "POST",
    url: "/form/{id}/webhooks",
    definition: "Add a New Webhook",
    explanation: "Webhooks can be used to send form submission data as an instant notification. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },
    {
        name: "webhookURL",
        description: "Webhook URL is where form data will be posted when form is submitted. ",
        example: "http://my.web.tld/handle.php",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        replace: "{webhookURL}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formWebHooksDELETE = {
    id:"delete-form-id-webhooks",
    type: "DELETE",
    url: "/form/{id}/webhooks/{whid}",
    definition: "Delete a webhook of a specific form",
    explanation: "Delete a webhook of a specific form",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: idDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },
    {
        name: "webhookID",
        description: "Webhook URL is where form data will be posted when form is submitted. You can get webhook IDs when you call /form/{formID}/webhooks.",
        example: "0",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{whid}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var folderID = {
    id:"folder-id",
    type: "GET",
    url: "/folder/{id}",
    definition: "Get Folder Details",
    explanation: "Get a list of forms in a folder, and other details about the form such as folder color. (<b>IMPORTANT: This endpoint is deprecated. Refer to the 'label' endpoints section for the updated endpoints.</b>)",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "Folder ID. Get a list of folders from /user/folders",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var postFolder = {
    id:"post-folder",
    type: "POST",
    url: "/folder",
    definition: "Create Folder",
    explanation: "Create a folder with specified parameters. (<b>IMPORTANT: This endpoint is deprecated. Refer to the 'label' endpoints section for the updated endpoints.</b>)",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "name",
        description: "Name of the folder",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{name}"
    },{
        name: "parent",
        description: "Parent id of the folder to be created",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: false,
        replace: "{parent}"
    },{
        name: "color",
        description: "Color of the folder Example: #FFFFFF",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: false,
        replace: "{color}"
    }],
    statusCodes: [{
        code: 400,
        reason: "No folder name supplied!"
    }],
}

var putFolderID = {
    id: "put-folder-id",
    type: "PUT",
    url: "/folder/{id}",
    definition: "Update Folder",
    explanation: "Update a folder with specified parameters. Also you can add forms to the folder. (<b>IMPORTANT: This endpoint is deprecated. Refer to the 'label' endpoints section for the updated endpoints.</b>)",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the folder",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "folderContent",
        description: "Name, color, parent of the specified folder. Also you can move forms to the specified folder.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true
    }],
    statusCodes: [{
        code: 404,
        reason: "Folder not found!"
    }],
}

var deleteFolderID = {
    id: "delete-folder-id",
    type: "DELETE",
    url: "/folder/{id}",
    definition: "Delete Folder",
    explanation: "Delete a folder and its subfolders. (<b>IMPORTANT: This endpoint is deprecated. Refer to the 'label' endpoints section for the updated endpoints.</b>)",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the folder",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }]
}

var getUserLabels = {
    id:"get-user-labels",
    type: "GET",
    url: "/user/labels",
    definition: "Get Label Details",
    explanation: "Get all labels in a user’s account, with optional support for including related resources via parameter.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "addResources",
        description: "Includes related label resources.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{addResources}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var deleteSubmission = {
    id:"delete-submission-id",
    type: "DELETE",
    url: "/submission/{id}",
    definition: "Delete Submission Data",
    explanation: "Delete a single submission. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Submission ID. You can get submission IDs when you call /form/{id}/submissions. View submissions directly on a browser: https://www.jotform.com/submission/<b>235194815571509962</b>.",
        example: "235194815571509962",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var editSubmission = {
    id:"post-submission-id",
    type: "POST",
    url: "/submission/{id}",
    definition: "Edit Submission Data",
    explanation: "Edit a single submission. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Submission ID. You can get submission IDs when you call /form/{id}/submissions. View submissions directly on a browser: https://www.jotform.com/submission/<b>235194815571509962</b>.",
        example: "235194815571509962",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "submission[1][first]",
        description: "Data entered in question 1. In this example the first question is a full name question. So, there are two fields in this question: firstName and lastName. These fields can be found by looking at the source code of the form.",
        example: "John",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        replace: "{id}"                   
    },{
        name: "submission[new]",
        description: "new is 1 if this submission is not read",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        replace: "{id}"                   
    },{
        name: "submission[flag]",
        description: "flag is 1 if this submission is marked as flagged.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var cloneForm = {
    id:"post-form-id-clone",
    type: "POST",
    url: "/form/{id}/clone",
    definition: "Clone Form",
    explanation: "Clone a single form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Form ID. You can get form IDs when you call /user/forms.",
        example: "31974353596870",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var deleteFormQuestion = {
    id:"delete-form-id-question-id",
    type: "DELETE",
    url: "/form/{id}/question/{qid}",
    definition: "Delete Form Question",
    explanation: "Delete a single form question. ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms.",
        example: "31974353596870",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "qid",
        description: "Question ID: You can get question IDs when you call /form/{id}/questions.",
        example: "2",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{qid}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdQuestionsPOST = {
    id:"post-form-id-questions",
    type: "POST",
    url: "/form/{id}/questions",
    definition: "Add new question to specified form",
    explanation: "Add new question to specified form. Form questions might have various <a href='properties/' target='_blank'>properties</a>. Examples: Is it required? Are there any validations such as 'numeric only'? ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "question[type]",
        description: "Type describes question field type.<br>Most commonly used types are control_textbox, control_textarea, control_dropdown control_radio, control_checkbox, control_fileupload, control_fullname, control_email and control_datetime",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,                
    },{
        name: "question[text]",
        description: "Label of your question",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "question[order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "question[name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdQuestionsPUT = {
    id:"put-form-id-questions",
    type: "PUT",
    url: "/form/{id}/questions",
    definition: "Add new questions to specified form",
    explanation: "Add new questions to specified form. Form questions might have various <a href='properties/' target='_blank'>properties</a>. Examples: Is it required? Are there any validations such as 'numeric only'? ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "questions",
        description: "New question's <a href='properties/?field=form' target='_blank'>properties</a>",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdQuestionQidPOST = {
    id:"post-form-id-question-id",
    type: "POST",
    url: "/form/{id}/question/{qid}",
    definition: "Add or edit a single question properties",
    explanation: "Edit a <a href='properties/' target='_blank'>question property</a> or add a new one. Form questions might have various properties. Examples: Is it required? Are there any validations such as 'numeric only'? ",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                   
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }, {
        name: "qid",
        description: qidDescription,
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{qid}"          
    },{
        name: "question[text]",
        description: "Label of your question",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "question[order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "question[name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdPropertiesPOST = {
    id:"post-form-id-properties",
    type: "POST",
    url: "/form/{id}/properties",
    definition: "Add or edit properties of a specific form",
    explanation: "Edit a <a href='properties/?field=form' target='_blank'>form property</a> or add a new one.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "properties[thankurl]",
        description: "Redirect user to a page after submission",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "properties[activeRedirect]",
        description: "What happens when someone submits the form. default shows them a default thank you message. thanktext and thankurl allows you to customize the thank you message or redirect user to another page.",
        type: "Enum",
        inputType: "select",
        parameterType:"post",
        required: false, 
        values: ['default', 'thanktext', 'thankurl']               
    },{
        name: "properties[formWidth]",
        description: "Resize form width",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,                
    },{
        name: "properties[labelWidth]",
        description: "Resize question label width",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formIdPropertiesPUT = {
    id:"put-form-id-properties",
    type: "PUT",
    url: "/form/{id}/properties",
    definition: "Add or edit properties of a specific form",
    explanation: "Edit a <a href='properties/?field=form' target='_blank'>form property</a> or add a new one.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",  
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')             
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    },{
        name: "formProperties",
        description: "New <a href='properties/?field=form' target='_blank'>properties</a> like label width and style.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userFormsPUT = {
    id:"put-user-forms",
    type: "PUT",
    url: "/user/forms",
    definition: "Create new forms",
    explanation: "Create new forms with questions, properties and email settings.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "formContent",
        description: "Questions, <a href='properties/' target='_blank'>properties</a> and emails of new form.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var formsPUT = {
    id:"put-forms",
    type: "PUT",
    url: "/form",
    definition: "Create new forms",
    explanation: "Create new forms with questions, properties and email settings.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "formContent",
        description: "Questions, <a href='properties/' target='_blank'>properties</a> and emails of new form.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true                
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var userFormsPOST = {
    id:"post-user-forms",
    type: "POST",
    url: "/user/forms",
    definition: "Create a new form",
    explanation: "Create new forms with questions, properties and email settings.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][type]",
        description: "Question field type",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][text]",
        description: "Label of your question" ,
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "properties[title]",
        description: "Form Title",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][type]",
        description: "Question field type",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][text]",
        description: "Label of your question" ,
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "properties[height]",
        description: "Height of form",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][type]",
        description: "Is this email a notification or a autoresponder? Notifications are sent to the owner of the form and autoresponders are sent to the person who fills the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][from]",
        description: "From email address on emails. This will only work if the email address is validated on the account.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][to]",
        description: "Recipient email address for the emails. If there are more than one email addresses separate them with a comma.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][subject]",
        description: "Subject of the email",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][html]",
        description: "Send email in HTML or plan text format. Set it to 1 if the email is HTML.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][body]",
        description: "Email contents",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }   ],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var getLabelId = {
    id:"get-label-id",
    type: "GET",
    url: "/label/{id}",
    definition: "Get Label Details",
    explanation: "Get the details of a label, including its name and color.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "Label ID",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};
var getLabelIdResources = {
    id:"get-label-id-resources",
    type: "GET",
    url: "/label/{id}/resources",
    definition: "Get Label Resources",
    explanation: "Get a list of assets in a label and their associated information.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "Label ID",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var postLabel = {
    id:"post-label",
    type: "POST",
    url: "/label",
    definition: "Create Label",
    explanation: "Create a label by defining attributes such as name and color.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "name",
        description: "Name of the label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        replace: "{name}"
    },{
        name: "color",
        description: "Color of the label Example: #FFFFFF",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        replace: "{color}"
    },{
        name: "parent",
        description: "Parent label ID",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        replace: "{parent}"
    }],
    statusCodes: [{
        code: 400,
        reason: "No label name supplied!"
    }],
};

var putLabel = {
    id: "put-label-id",
    type: "PUT",
    url: "/label/{id}",
    definition: "Create Label",
    explanation: "Update an existing label with specified parameters, such as name and color",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the label",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "property",
        description: "Properties to be updated such as name and color, in JSON format.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"post",
        required: true,
    }],
    statusCodes: [{
        code: 400,
        reason: "No label name supplied!"
    }],
};

var putLabelIdAddResources = {
    id: "put-label-id-add-resources",
    type: "PUT",
    url: "/label/{id}/add-resources",
    definition: "Add Resources to Label",
    explanation: "Add the specified assets, identified by their IDs and types, into a label.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the label",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "resources",
        description: "Resources to be added to the label, in JSON format.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true,
    }],
    statusCodes: [{
        code: 400,
        reason: "No resources supplied!"
    }],
};

var putLabelIdRemoveResources = {
    id: "put-label-id-remove-resources",
    type: "PUT",
    url: "/label/{id}/remove-resources",
    definition: "Remove Resources from Label",
    explanation: "Remove the specified assets, identified by their IDs and types, from a label.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the label",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    },{
        name: "resources",
        description: "Resources to be removed from the label, in JSON format.",
        type: "JSON",
        inputType: "textarea",
        parameterType:"JSON",
        required: true,
    }],
    statusCodes: [{
        code: 400,
        reason: "No resources supplied!"
    }],
};

var deleteLabelId = {
    id: "delete-label-id",
    type: "DELETE",
    url: "/label/{id}",
    definition: "Delete Label",
    explanation: "Delete a label along with all its sublabels.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')   
    },{
        name: "id",
        description: "ID of the label",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"
    }],
    statusCodes: [{
        code: 400,
        reason: "No label id supplied!"
    }],
};

var formsPOST = {
    id:"post-forms",
    type: "POST",
    url: "/form",
    definition: "Create a new form",
    explanation: "Create new forms with questions, properties and email settings.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][type]",
        description: "Question field type",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][text]",
        description: "Label of your question" ,
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[1][name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "properties[title]",
        description: "Form Title",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][type]",
        description: "Question field type",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][text]",
        description: "Label of your question" ,
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][order]",
        description: "Order defines the location of the question in the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "questions[2][name]",
        description: "Slug of question label",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "properties[height]",
        description: "Height of form",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][type]",
        description: "Is this email a notification or a autoresponder? Notifications are sent to the owner of the form and autoresponders are sent to the person who fills the form.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][from]",
        description: "From email address on emails. This will only work if the email address is validated on the account.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][to]",
        description: "Recipient email address for the emails. If there are more than one email addresses separate them with a comma.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][subject]",
        description: "Subject of the email",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][html]",
        description: "Send email in HTML or plan text format. Set it to 1 if the email is HTML.",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "emails[1][body]",
        description: "Email contents",
        type: "String",
        inputType: "text",
        parameterType:"post",
        required: false,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    }   ],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var deleteForm = {
    id:"delete-form-id",
    type: "DELETE",
    url: "/form/{id}",
    definition: "Delete a form",
    explanation: "Delete an existing form.",
    parameters: [{
        name: "apikey",
        description: apikeyDescription,
        type: "String",
        inputType: "text",
        parameterType:"query",
        required: true,
        value: (typeof window.jotCookie !== 'undefined') ? window.jotCookie.readCookie("jf_auth") : readCookie('jf_auth')                       
    },{
        name: "id",
        description: "Form ID: You can get form IDs when you call /user/forms. Question ID: You can get question IDs when you call /form/{id}/questions.",
        type: "String",
        inputType: "text",
        parameterType:"url",
        required: true,
        replace: "{id}"                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};

var systemPlanName = {
    id:"system-plan-planName",
    type: "GET",
    url: "/system/plan/{planName}",
    definition: "Get details of a plan",
    explanation: "Get limit and prices of a plan.",
    parameters: [{
        name: "planName",
        description: "Name of the requested plan. FREE, BRONZE etc.",
        type: "String",
        inputType: "select",
        parameterType:"url",
        required: true,
        replace: "{planName}",
        values: ['FREE', 'BRONZE', 'SILVER', 'GOLD','PLATINUM']                   
    }],
    statusCodes: [{
        code: 404,
        reason: "User not found"
    }],
};


var requestModels = [
    userInfo
    ,userUsage    
    ,userSubmissions
    ,userSubusers
    ,userFolders
    ,userReports
    ,userLogin
    ,userLogout
    ,userSettings
    ,userSettingsPOST
    ,userHistory

    ,getLabelId
    ,getLabelIdResources
    ,postLabel
    ,putLabel
    ,putLabelIdAddResources
    ,putLabelIdRemoveResources
    ,deleteLabelId

    ,userForms
    ,userFormsPOST
    ,formsPOST
    ,userFormsPUT
    ,getUserLabels
    ,formsPUT

    ,formId
    ,deleteForm

    ,cloneForm
    
    ,formIdQuestions
    ,formIdQuestionsPOST
    ,formIdQuestionsPUT
    
    ,formIdQuestionQid
    ,formIdQuestionQidPOST
    ,deleteFormQuestion

    ,formIdProperties
    ,formIdPropertiesPOST
    ,formIdPropertiesPUT
    ,formIdPropertiesProperty

    ,formIdReports
    ,formIdReportsPOST

    ,formIdFiles
    
    ,formWebHooks
    ,formWebHooksPOST
    ,formWebHooksDELETE

    ,formIdSubmissions
    ,formIdSubmissionsPOST
    ,formIdSubmissionsPUT

    ,submissionID
    ,editSubmission
    ,deleteSubmission

    ,reportID
    ,deleteReport
    ,folderID
    ,postFolder
    ,putFolderID
    ,deleteFolderID
    ,systemPlanName

    // ,userApps
    // ,userInvoices
    // ,userKeys
    // ,userRewards
]
