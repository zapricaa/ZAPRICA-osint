/** @type {import('next').NextConfig} */
const backendUrl = process.env.INTERNAL_API_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    allowedDevOrigins: ['192.168.*.*', 'localhost:*', '127.0.0.1:*', '10.*.*.*'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
