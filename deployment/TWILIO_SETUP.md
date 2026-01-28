# Twilio Webhook Setup for GarageAI

## 1. Prerequisites
- A Twilio Account with an active phone number.
- Your GarageAI server running and exposed to the internet (via ngrok or Cloud Run).

## 2. Get your Server URL
- **Ngrok**: Copy the forwarded URL (e.g., `https://abcdef.ngrok-free.app`).
- **Cloud Run**: Copy the Service URL (e.g., `https://garage-ai-bridge-xyz.a.run.app`).

## 3. Configure Twilio

### Option A: TwiML Bin (Recommended for testing)
1. Go to **Twilio Console** > **Developer Tools** > **TwiML Bins**.
2. Click **Create New TwiML Bin**.
3. **Friendly Name**: `GarageAI Stream`.
4. **TwiML**:
   Replace `{{YOUR_SERVER_DOMAIN}}` with your actual domain (without `https://`).

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
       <Connect>
           <Stream url="wss://{{YOUR_SERVER_DOMAIN}}/ws/twilio">
               <Parameter name="aCustomParameter" value="someValue" />
           </Stream>
       </Connect>
   </Response>
   ```
   *Example*: If your ngrok URL is `https://12345.ngrok.io`, the url is `wss://12345.ngrok.io/ws/twilio`.

5. Click **Save**.
6. Go to **Phone Numbers** > **Manage** > **Active Numbers**.
7. Click your Dutch phone number.
8. Scroll to **Voice & Fax**.
9. Under **A Call Comes In**, select **TwiML Bin**.
10. Select `GarageAI Stream`.
11. Click **Save**.

### Option B: Webhook (Direct)
1. Go to your Phone Number settings.
2. Under **A Call Comes In**, select **Webhook**.
3. Enter your URL: `https://{{YOUR_SERVER_DOMAIN}}/voice` (Note: We haven't built a `/voice` HTTP endpoint yet, we strictly used the WebSocket directly via TwiML. Use Option A or serve the XML from FastAPI if you add a standard HTTP route).
   
   *Recommendation*: Stick to Option A (TwiML Bin) as it isolates the logic from your server needing to host the XML.

## 4. Testing
1. Call your Twilio number.
2. You should see "Twilio WebSocket connection accepted" in your server logs.
3. Start speaking.
