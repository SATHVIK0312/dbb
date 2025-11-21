using System.Collections;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace JPMCGenAI_v1._0
{
    // ──────────────────────────────────────────────────────────────
    // AUTH, PROJECT, USER MODELS
    // ──────────────────────────────────────────────────────────────
    public class LoginCreate
    {
        public string username { get; set; }
        public string password { get; set; }
    }

    public class LoginResponse
    {
        public string userid { get; set; }
        public string role { get; set; }
        public string token { get; set; }
        public List<Project> projects { get; set; }
    }

    public class Project
    {
        public string projectid { get; set; }
        public string title { get; set; }
        public string startdate { get; set; }
        public string projecttype { get; set; }
        public string description { get; set; }
    }

    public class RegisterCreate
    {
        public string name { get; set; }
        public string mail { get; set; }
        public string password { get; set; }
        public string role { get; set; }
    }
}
