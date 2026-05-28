using Microsoft.AspNetCore.Mvc;

namespace SampleDotNet.Controllers;

[ApiController]
[Route("api/[controller]")]
public class OrdersController : ControllerBase
{
    [HttpGet]
    public IActionResult GetOrders()
    {
        var orders = new[]
        {
            new { id = 1, customer = "My Team", total = 42.50 },
            new { id = 2, customer = "Platform Squad", total = 198.99 }
        };

        return Ok(orders);
    }

    [HttpPost]
    public IActionResult CreateOrder([FromBody] OrderRequest request)
    {
        var response = new { id = 3, customer = request.Customer, total = request.Total, status = "created" };
        return CreatedAtAction(nameof(GetOrders), response);
    }
}

public record OrderRequest(string Customer, decimal Total);
