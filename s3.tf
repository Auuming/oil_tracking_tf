# s3.tf

# 1. S3 Bucket for the Frontend Code
resource "aws_s3_bucket" "frontend" {
  bucket        = "${local.name}-frontend-app-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = local.tags
}

# 2. S3 Bucket Policy (Allowing CloudFront to read the files securely)
resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            # This references the CDN created in cdn.tf
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })
}

# 1. Upload index.html
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "index.html"
  source       = "frontend/index.html" 
  etag         = filemd5("frontend/index.html")
  content_type = "text/html"
}

# 2. Upload styles.css
resource "aws_s3_object" "styles_css" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "styles.css"
  source       = "frontend/styles.css"
  etag         = filemd5("frontend/styles.css")
  content_type = "text/css"
}

# 3. Upload app.js
resource "aws_s3_object" "app_js" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "app.js"
  source       = "frontend/app.js"
  etag         = filemd5("frontend/app.js")
  content_type = "application/javascript"
}

# 4. Dynamically create config.js with the live API URL
resource "aws_s3_object" "config_js" {
  bucket       = aws_s3_bucket.frontend.id
  key          = "config.js"
  content      = "const CONFIG = { API_BASE_URL: \"${aws_apigatewayv2_api.http.api_endpoint}\" };"
  content_type = "application/javascript"
}