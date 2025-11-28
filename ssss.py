else if (status == "SCRIPT")
{
    AppendLog("[SCRIPT] Generated script received");

    // full script
    if (root.TryGetProperty("script", out var scriptProp))
    {
        AppendLog("\n----- GENERATED SCRIPT START -----\n");
        AppendLog(scriptProp.GetString());
        AppendLog("\n----- GENERATED SCRIPT END -----\n");
    }
    // preview (fallback)
    else if (root.TryGetProperty("script_preview", out var previewProp))
    {
        AppendLog("\n----- GENERATED SCRIPT PREVIEW -----\n");
        AppendLog(previewProp.GetString());
        AppendLog("\n[Script too long, preview only]\n");
    }

    continue;
}
