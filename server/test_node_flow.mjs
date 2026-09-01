import { GoogleFlowNodeClient } from "./google_flow_node.mjs";

const client = new GoogleFlowNodeClient();
console.log("Testing Node Google Flow Client...");
try {
  const job = await client.generateVideo("A cinematic 3D modern luxury villa in Gurgaon with infinity pool and palm trees", 5);
  console.log("SUCCESS:", job);
} catch (e) {
  console.error("ERROR:", e.message);
}
