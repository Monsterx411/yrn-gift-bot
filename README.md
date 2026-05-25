![tw-banner](https://github.com/thirdweb-example/next-starter/assets/57885104/20c8ce3b-4e55-4f10-ae03-2fe4743a5ee8)

# thirdweb-next-starter

Starter template to build an onchain react native app with [thirdweb](https://thirdweb.com/) and [next](https://nextjs.org/).

## Installation

Install the template using [thirdweb create](https://portal.thirdweb.com/cli/create)

```bash
  npx thirdweb create app --next
```

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file:

`NEXT_PUBLIC_CLIENT_ID`

To learn how to create a client ID, refer to the [client documentation](https://portal.thirdweb.com/typescript/v5/client).

## Run locally

Install dependencies

```bash
yarn install
```

Start development server

```bash
yarn dev
```

Create a production build

```bash
yarn build
```

Preview the production build

```bash
yarn start
```

## Deployment

This project can deploy to any platform that supports Next.js.

For thirdweb deployment, ensure `NEXT_PUBLIC_CLIENT_ID` is set in the deployed app's environment variables.

If you are deploying to Vercel, you can use the same command structure as the local build.

## Resources

- [Documentation](https://portal.thirdweb.com/typescript/v5)
- [Templates](https://thirdweb.com/templates)
- [YouTube](https://www.youtube.com/c/thirdweb)
- [Blog](https://blog.thirdweb.com)

## Need help?

For help or feedback, please [visit our support site](https://thirdweb.com/support)

## Docker (optional)

Build a production Docker image for the Next.js app:

```bash
docker build -t tel-gift-card-bot:latest .
```

Run the image (set `NEXT_PUBLIC_CLIENT_ID` in the environment):

```bash
docker run -e NEXT_PUBLIC_CLIENT_ID=your-client-id -p 3000:3000 tel-gift-card-bot:latest
```

## CI / Deployment

A simple GitHub Actions workflow (`.github/workflows/ci.yml`) is included to build the app on push and PR. For auto-deploy to Vercel, link this repository in your Vercel dashboard and set `NEXT_PUBLIC_CLIENT_ID` in your project environment variables.

If you prefer container-based deployment, use the `Dockerfile` provided and push the built image to your registry.
