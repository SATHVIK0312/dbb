public async Task<HttpResponseMessage> PostFileAsync(string endpoint, string filePath)
{
    using var content = new MultipartFormDataContent();

    var fileBytes = await File.ReadAllBytesAsync(filePath);
    var fileContent = new ByteArrayContent(fileBytes);
    fileContent.Headers.ContentType = MediaTypeHeaderValue.Parse("application/octet-stream");

    content.Add(
        fileContent,
        "file",                         // MUST match FastAPI parameter name
        Path.GetFileName(filePath)
    );

    return await _httpClient.PostAsync(endpoint, content);
}
