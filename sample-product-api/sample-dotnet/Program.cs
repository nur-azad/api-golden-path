//var builder = WebApplication.CreateBuilder(args);

//builder.Services.AddControllers();
//builder.Services.AddEndpointsApiExplorer();
//builder.Services.AddSwaggerGen();

//// Observability note: in a real platform sample, add OpenTelemetry packages and middleware here.
//// For a small runnable demo, this project focuses on the API and Swagger contract surface.

//var app = builder.Build();

//if (app.Environment.IsDevelopment())
//{
//    app.UseSwagger();
//    app.UseSwaggerUI();
//}

//app.UseRouting();
//app.UseAuthorization();
//app.MapControllers();
//app.Run();

var builder = WebApplication.CreateBuilder(args);

// 1. Register the Swagger Generator into the dependency injection container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.Models.OpenApiInfo
    {
        Title = "Sample Orders API",
        Version = "1.0.0",
        Description = "API for managing orders"
    });
});

var app = builder.Build();

// 2. Activate the pipeline endpoints when running locally
if (app.Environment.IsDevelopment())
{
    app.UseSwagger(); // Generates the raw JSON schema file
    app.UseSwaggerUI(); // Hosts the interactive web dashboard
}

app.UseAuthorization();
app.MapControllers();
app.Run();