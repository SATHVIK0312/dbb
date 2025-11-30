// ---- FIX: robust parsing for "normalized" field ----
List<Dictionary<string, object>> normalizedSteps = null;
var normalizedRaw = item["normalized"];

// Case 1 → already correct type
if (normalizedRaw is List<Dictionary<string, object>> directList)
{
    normalizedSteps = directList;
}
// Case 2 → List<object>
else if (normalizedRaw is List<object> objList)
{
    normalizedSteps = objList
        .Select(o =>
            JsonSerializer.Deserialize<Dictionary<string, object>>(
                JsonSerializer.Serialize(o)
            )
        ).ToList();
}
// Case 3 → JsonElement array (MOST COMMON)
else if (normalizedRaw is JsonElement elem && elem.ValueKind == JsonValueKind.Array)
{
    normalizedSteps = elem.EnumerateArray()
        .Select(x =>
            JsonSerializer.Deserialize<Dictionary<string, object>>(x.GetRawText())
        ).ToList();
}
// Case 4 → give up
else
{
    throw new Exception("Invalid normalized steps (unexpected format)");
}
