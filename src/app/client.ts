import { createThirdwebClient } from "thirdweb";

// Factory that creates a thirdweb client on the client side.
export function getClient() {
  const clientId =
    process.env.NEXT_PUBLIC_CLIENT_ID || process.env.NEXT_PUBLIC_TEMPLATE_CLIENT_ID;

  if (!clientId) {
    throw new Error("No client ID provided");
  }

  return createThirdwebClient({ clientId });
}

export default getClient;
