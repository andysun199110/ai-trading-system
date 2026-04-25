//+------------------------------------------------------------------+
//|                                              GoldAITraderEA.mq5  |
//|                                    AI-Powered Gold Trading System|
//|                                   Client Execution EA (MQL5)     |
//+------------------------------------------------------------------+
#property copyright "Gold AI Trading System"
#property version   "1.00"
#property description "Client-side execution EA with WebRequest signal polling"
#property strict

//--- Input Parameters
input group "=== API Configuration ==="
input string Inp_ApiBaseUrl       = "https://api.example.com/api/v1";  // API Base URL
input string Inp_LicenseKey       = "";                                 // License Key
input int    Inp_PollIntervalSec  = 30;                                 // Poll Interval (seconds)

input group "=== Account Settings ==="
input string Inp_AccountServer    = "";                                 // MT5 Server Name (optional override)
input bool   Inp_ShadowMode       = true;                               // Shadow Mode (no execution)

input group "=== Execution Safety ==="
input bool   Inp_RequireServerRiskParams = true;                        // Require volume/sl/tp from AI signal
input bool   Inp_UseFallbackRiskParams   = false;                       // Use fallback values only if server fields are missing
input double Inp_DefaultLotSize          = 0.01;                        // Fallback lot size (disabled by default)
input int    Inp_StopLossPoints          = 500;                         // Fallback stop loss points (disabled by default)
input int    Inp_TakeProfitPoints        = 1000;                        // Fallback take profit points (disabled by default)
input double Inp_MaxLotCap               = 1.00;                        // Local safety cap for max lot size
input bool   Inp_AllowTrading            = false;                       // Allow Live Trading (default: OFF)

//--- Global Variables
string g_SessionToken = "";
datetime g_LastPollTime = 0;
datetime g_LastSuccessfulPoll = 0;
string g_LastSignalId = "";
string g_LastSignalAction = "";
string g_LastExecutionResult = "";
int g_LastHttpCode = 0;
string g_LastHttpError = "";
bool g_IsConnected = false;
bool g_ProtectiveMode = false;
string g_ProcessedSignalsFile = "GoldAI_processed_signals.csv";
ulong g_MagicNumber = 2026042401;

//--- UI Panel Variables
int g_PanelX = 10, g_PanelY = 30;
int g_PanelWidth = 320, g_PanelHeight = 450;
color g_ColorBg = clrWhite;
color g_ColorHeader = clrDarkBlue;
color g_ColorText = clrBlack;
color g_ColorValue = clrDarkGreen;
color g_ColorError = clrRed;
color g_ColorWarning = clrOrange;
color g_ColorSuccess = clrGreen;

//--- Position Tracking
double g_PositionLots = 0;
double g_PositionEntryPrice = 0;
double g_PositionSL = 0;
double g_PositionTP = 0;
ENUM_POSITION_TYPE g_PositionType = POSITION_TYPE_BUY;
double g_PositionCurrentPrice = 0;
double g_PositionProfit = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   PrintFormat("[GoldAI] Initializing EA v1.00");
   PrintFormat("[GoldAI] API: %s", Inp_ApiBaseUrl);
   PrintFormat("[GoldAI] Mode: %s", Inp_ShadowMode ? "SHADOW" : "LIVE");
   PrintFormat("[GoldAI] Account: %d @ %s", AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER));
   PrintFormat("[GoldAI] Risk params source: %s", Inp_RequireServerRiskParams ? "SERVER_REQUIRED" : (Inp_UseFallbackRiskParams ? "SERVER_OR_FALLBACK" : "SERVER_PREFERRED"));

   RestoreLocalState();

   if(!Authenticate())
   {
      Print("[GoldAI] Initial auth failed, will retry on first poll");
      g_SessionToken = "";
   }

   EventSetTimer(Inp_PollIntervalSec);

   Print("[GoldAI] Initialization complete");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   DeleteAllObjects(0, "GoldAI_");
   PrintFormat("[GoldAI] Deinitialized (reason: %d)", reason);
}

//+------------------------------------------------------------------+
void OnTick()
{
   UpdatePositionInfo();
   DrawUIPanel();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(g_SessionToken == "")
   {
      if(!Authenticate())
      {
         Print("[GoldAI] Auth failed, will retry");
         return;
      }
   }

   Heartbeat();
   PollSignals();
   SuperviseOpenPositions();
}

//+------------------------------------------------------------------+
void RestoreLocalState()
{
   if(FileIsExist(g_ProcessedSignalsFile))
   {
      Print("[GoldAI] Restored processed signals ledger");
      return;
   }

   int handle = FileOpen(g_ProcessedSignalsFile, FILE_WRITE|FILE_CSV);
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle, "signal_id", "timestamp", "action", "result");
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
bool Authenticate()
{
   Print("[GoldAI] Authenticating...");

   string accountServer = (Inp_AccountServer != "") ? Inp_AccountServer : AccountInfoString(ACCOUNT_SERVER);
   string url = Inp_ApiBaseUrl + "/auth/activate";
   uchar postData[];
   string json = StringFormat("{\"license_key\":\"%s\",\"account_login\":\"%d\",\"account_server\":\"%s\"}",
                              Inp_LicenseKey,
                              AccountInfoInteger(ACCOUNT_LOGIN),
                              accountServer);

   StringToBuffer(json, postData);

   uchar resultData[];
   string responseHeaders;
   string headers = "Content-Type: application/json\r\n";
   int resultCode = WebRequest("POST", url, headers, 5000, postData, resultData, responseHeaders);

   g_LastHttpCode = resultCode;

   if(resultCode < 200 || resultCode >= 300)
   {
      g_LastHttpError = "Auth HTTP: " + IntegerToString(resultCode);
      Print("[GoldAI] Auth failed: ", g_LastHttpError, " response=", CharArrayToString(resultData));
      g_IsConnected = false;
      return false;
   }

   string response = CharArrayToString(resultData);
   string token = GetJsonString(response, "token", "");

   if(token != "")
   {
      g_SessionToken = token;
      g_IsConnected = true;
      g_LastHttpError = "";
      Print("[GoldAI] Auth successful");
      return true;
   }

   g_LastHttpError = "Invalid response: token missing";
   Print("[GoldAI] Auth failed: ", response);
   g_IsConnected = false;
   return false;
}

//+------------------------------------------------------------------+
void Heartbeat()
{
   if(g_SessionToken == "") return;

   string url = Inp_ApiBaseUrl + "/auth/heartbeat";
   uchar postData[];
   string json = StringFormat("{\"token\":\"%s\"}", g_SessionToken);

   StringToBuffer(json, postData);

   uchar resultData[];
   string responseHeaders;

   string headers = "Content-Type: application/json\r\n";
   int resultCode = WebRequest("POST", url, headers, 5000, postData, resultData, responseHeaders);

   g_LastHttpCode = resultCode;
   if(resultCode < 200 || resultCode >= 300)
   {
      g_LastHttpError = "Heartbeat failed";
      g_IsConnected = false;
      if(resultCode == 401 || resultCode == 403)
         g_SessionToken = "";
      return;
   }

   g_IsConnected = true;
   g_LastHttpError = "";
}

//+------------------------------------------------------------------+
void PollSignals()
{
   if(g_SessionToken == "") return;

   g_LastPollTime = TimeCurrent();

   string url = Inp_ApiBaseUrl + "/signals/poll?token=" + g_SessionToken;

   uchar resultData[];
   string responseHeaders;

   string headers = "";
   uchar requestData[];
   ArrayResize(requestData, 0);
   int resultCode = WebRequest("GET", url, headers, 5000, requestData, resultData, responseHeaders);

   g_LastHttpCode = resultCode;

   if(resultCode < 200 || resultCode >= 300)
   {
      g_LastHttpError = "Poll failed: " + IntegerToString(resultCode);
      g_IsConnected = false;
      Print("[GoldAI] ", g_LastHttpError);
      return;
   }

   g_LastSuccessfulPoll = TimeCurrent();
   g_LastHttpError = "";
   g_IsConnected = true;

   string response = CharArrayToString(resultData);
   ProcessSignals(response);
}

//+------------------------------------------------------------------+
void ProcessSignals(string jsonResponse)
{
   if(StringFind(jsonResponse, "\"signals\":[]") > 0 || StringFind(jsonResponse, "\"signals\": []") > 0)
      return;

   int sigIdPos = StringFind(jsonResponse, "\"signal_id\":\"");
   if(sigIdPos < 0) return;

   int sigIdStart = sigIdPos + 13;
   int sigIdEnd = StringFind(jsonResponse, "\"", sigIdStart);
   string signalId = StringSubstr(jsonResponse, sigIdStart, sigIdEnd - sigIdStart);

   if(IsDuplicateSignal(signalId))
      return;

   g_LastSignalId = signalId;

   int actionPos = StringFind(jsonResponse, "\"action\":\"");
   if(actionPos < 0) return;

   int actionStart = actionPos + 10;
   int actionEnd = StringFind(jsonResponse, "\"", actionStart);
   string action = StringSubstr(jsonResponse, actionStart, actionEnd - actionStart);

   g_LastSignalAction = action;

   string side = GetJsonString(jsonResponse, "side", "buy");
   double volume = 0.0;
   double sl = 0.0;
   double tp = 0.0;
   bool hasVolume = TryGetJsonNumber(jsonResponse, "volume", volume);
   bool hasSL = TryGetJsonNumber(jsonResponse, "sl", sl) || TryGetJsonNumber(jsonResponse, "stop_loss", sl);
   bool hasTP = TryGetJsonNumber(jsonResponse, "tp", tp) || TryGetJsonNumber(jsonResponse, "take_profit", tp);

   int slPoints = 0;
   int tpPoints = 0;
   bool hasSLPoints = TryGetJsonInt(jsonResponse, "sl_points", slPoints) || TryGetJsonInt(jsonResponse, "stop_loss_points", slPoints);
   bool hasTPPoints = TryGetJsonInt(jsonResponse, "tp_points", tpPoints) || TryGetJsonInt(jsonResponse, "take_profit_points", tpPoints);

   if(!hasSL && hasSLPoints && slPoints > 0)
   {
      sl = CalcPriceFromPoints(side, true, slPoints);
      hasSL = (sl > 0);
   }
   if(!hasTP && hasTPPoints && tpPoints > 0)
   {
      tp = CalcPriceFromPoints(side, false, tpPoints);
      hasTP = (tp > 0);
   }

   if(Inp_UseFallbackRiskParams)
   {
      if(!hasVolume)
      {
         volume = Inp_DefaultLotSize;
         hasVolume = (volume > 0);
      }
      if(!hasSL && Inp_StopLossPoints > 0)
      {
         sl = CalcPriceFromPoints(side, true, Inp_StopLossPoints);
         hasSL = (sl > 0);
      }
      if(!hasTP && Inp_TakeProfitPoints > 0)
      {
         tp = CalcPriceFromPoints(side, false, Inp_TakeProfitPoints);
         hasTP = (tp > 0);
      }
   }

   if(hasVolume && Inp_MaxLotCap > 0 && volume > Inp_MaxLotCap)
   {
      PrintFormat("[GoldAI] Volume %.2f exceeds local safety cap %.2f for signal %s", volume, Inp_MaxLotCap, signalId);
      g_LastExecutionResult = "volume_exceeds_cap";
      MarkSignalProcessed(signalId, action, g_LastExecutionResult);
      ReportExecution(signalId, g_LastExecutionResult);
      return;
   }

   if(action == "open" && Inp_RequireServerRiskParams && (!hasVolume || !hasSL || !hasTP))
   {
      PrintFormat("[GoldAI] Signal %s missing required risk params (volume=%s, sl=%s, tp=%s)",
                  signalId,
                  hasVolume ? "yes" : "no",
                  hasSL ? "yes" : "no",
                  hasTP ? "yes" : "no");
      g_LastExecutionResult = "signal_missing_risk_params";
      MarkSignalProcessed(signalId, action, g_LastExecutionResult);
      ReportExecution(signalId, g_LastExecutionResult);
      return;
   }

   if(Inp_ShadowMode)
   {
      string volumeStr = hasVolume ? DoubleToString(volume, 2) : "N/A";
      PrintFormat("[GoldAI] SHADOW MODE: Would execute %s %s %s lots", action, side, volumeStr);
      g_LastExecutionResult = "shadow_skipped";
      MarkSignalProcessed(signalId, action, g_LastExecutionResult);
      ReportExecution(signalId, g_LastExecutionResult);
      return;
   }

   if(!Inp_AllowTrading)
   {
      string volumeStr = hasVolume ? DoubleToString(volume, 2) : "N/A";
      PrintFormat("[GoldAI] Trading disabled: %s %s %s lots", action, side, volumeStr);
      g_LastExecutionResult = "trading_disabled";
      MarkSignalProcessed(signalId, action, g_LastExecutionResult);
      ReportExecution(signalId, g_LastExecutionResult);
      return;
   }

   bool success = ExecuteTrade(action, side, volume, sl, tp, signalId);
   g_LastExecutionResult = success ? "executed" : "failed";
   MarkSignalProcessed(signalId, action, g_LastExecutionResult);
   ReportExecution(signalId, g_LastExecutionResult);
}

//+------------------------------------------------------------------+
string GetJsonString(string jsonResponse, string fieldName, string defaultValue="")
{
   string pattern = "\"" + fieldName + "\":\"";
   int pos = StringFind(jsonResponse, pattern);
   if(pos < 0)
      return defaultValue;

   int start = pos + StringLen(pattern);
   int end = StringFind(jsonResponse, "\"", start);
   if(end < 0)
      return defaultValue;

   return StringSubstr(jsonResponse, start, end - start);
}

//+------------------------------------------------------------------+
bool TryGetJsonNumber(string jsonResponse, string fieldName, double &value)
{
   string pattern = "\"" + fieldName + "\":";
   int pos = StringFind(jsonResponse, pattern);
   if(pos < 0)
      return false;

   int start = pos + StringLen(pattern);
   while(start < StringLen(jsonResponse))
   {
      ushort ch = StringGetCharacter(jsonResponse, start);
      if(ch != ' ' && ch != '"')
         break;
      start++;
   }

   int end = start;
   while(end < StringLen(jsonResponse))
   {
      ushort ch = StringGetCharacter(jsonResponse, end);
      if(ch == ',' || ch == '}' || ch == ']' || ch == '"')
         break;
      end++;
   }

   if(end <= start)
      return false;

   string raw = TrimString(StringSubstr(jsonResponse, start, end - start));
   if(raw == "null" || raw == "")
      return false;

   value = StringToDouble(raw);
   return true;
}

//+------------------------------------------------------------------+
bool TryGetJsonInt(string jsonResponse, string fieldName, int &value)
{
   double tmp = 0.0;
   if(!TryGetJsonNumber(jsonResponse, fieldName, tmp))
      return false;
   value = (int)MathRound(tmp);
   return true;
}

//+------------------------------------------------------------------+
string TrimString(string value)
{
   int start = 0;
   int end = StringLen(value) - 1;

   while(start <= end && StringGetCharacter(value, start) == ' ')
      start++;

   while(end >= start && StringGetCharacter(value, end) == ' ')
      end--;

   if(end < start)
      return "";

   return StringSubstr(value, start, end - start + 1);
}

//+------------------------------------------------------------------+
double CalcPriceFromPoints(string side, bool isStopLoss, int points)
{
   if(points <= 0)
      return 0.0;

   string sideLower = side;
   StringToLower(sideLower);
   bool isBuy = (StringCompare(sideLower, "buy") == 0);
   double openPrice = isBuy ? SymbolInfoDouble(Symbol(), SYMBOL_ASK) : SymbolInfoDouble(Symbol(), SYMBOL_BID);
   double offset = points * _Point;

   if(isBuy)
      return isStopLoss ? (openPrice - offset) : (openPrice + offset);

   return isStopLoss ? (openPrice + offset) : (openPrice - offset);
}

//+------------------------------------------------------------------+
bool ExecuteTrade(string action, string side, double volume, double sl, double tp, string signalId)
{
   if(action == "open")
   {
      ENUM_ORDER_TYPE orderType = (side == "buy") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

      MqlTradeRequest request = {};
      MqlTradeResult result = {};

      request.action = TRADE_ACTION_DEAL;
      request.symbol = Symbol();
      request.volume = volume;
      request.type = orderType;
      request.price = (orderType == ORDER_TYPE_BUY) ? SymbolInfoDouble(Symbol(), SYMBOL_ASK) : SymbolInfoDouble(Symbol(), SYMBOL_BID);
      request.sl = sl;
      request.tp = tp;
      request.magic = g_MagicNumber;
      request.comment = "GoldAI:" + signalId;

      if(!OrderSend(request, result))
      {
         PrintFormat("[GoldAI] Order failed: %s", result.comment);
         return false;
      }

      PrintFormat("[GoldAI] Order executed: ticket=%d, price=%.5f", result.order, result.price);
      return true;
   }
   if(action == "close")
      return CloseAllPositions();

   return false;
}

//+------------------------------------------------------------------+
bool CloseAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == Symbol())
      {
         MqlTradeRequest request = {};
         MqlTradeResult result = {};

         request.action = TRADE_ACTION_DEAL;
         request.position = ticket;
         request.symbol = Symbol();
         request.volume = PositionGetDouble(POSITION_VOLUME);
         request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
         request.price = (request.type == ORDER_TYPE_SELL) ? SymbolInfoDouble(Symbol(), SYMBOL_BID) : SymbolInfoDouble(Symbol(), SYMBOL_ASK);

         if(!OrderSend(request, result))
         {
            PrintFormat("[GoldAI] Close failed: %s", result.comment);
            return false;
         }
      }
   }
   Print("[GoldAI] All positions closed");
   return true;
}

//+------------------------------------------------------------------+
bool IsDuplicateSignal(string signalId)
{
   if(!FileIsExist(g_ProcessedSignalsFile)) return false;

   int handle = FileOpen(g_ProcessedSignalsFile, FILE_READ|FILE_CSV);
   if(handle == INVALID_HANDLE) return false;

   // Skip header row
   if(!FileIsEnding(handle))
   {
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
      FileReadString(handle);
   }

   while(!FileIsEnding(handle))
   {
      string existingSignalId = FileReadString(handle);
      FileReadString(handle); // timestamp
      FileReadString(handle); // action
      FileReadString(handle); // result

      if(existingSignalId == signalId)
      {
         FileClose(handle);
         return true;
      }
   }

   FileClose(handle);
   return false;
}

//+------------------------------------------------------------------+
void MarkSignalProcessed(string signalId, string action, string result)
{
   int handle = FileOpen(g_ProcessedSignalsFile, FILE_READ|FILE_WRITE|FILE_CSV);
   if(handle == INVALID_HANDLE)
      handle = FileOpen(g_ProcessedSignalsFile, FILE_WRITE|FILE_CSV);

   if(handle != INVALID_HANDLE)
   {
      FileSeek(handle, 0, SEEK_END);
      FileWrite(handle, signalId, TimeToString(TimeCurrent()), action, result);
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
void ReportExecution(string signalId, string status)
{
   if(g_SessionToken == "") return;

   string url = Inp_ApiBaseUrl + "/execution/report";
   uchar postData[];
   string json = StringFormat("{\"token\":\"%s\",\"signal_id\":\"%s\",\"status\":\"%s\",\"payload\":{}}",
                              g_SessionToken, signalId, status);

   StringToBuffer(json, postData);

   uchar resultData[];
   string responseHeaders;

   string headers = "Content-Type: application/json\r\n";
   WebRequest("POST", url, headers, 5000, postData, resultData, responseHeaders);
}

//+------------------------------------------------------------------+
void SuperviseOpenPositions()
{
   if(g_ProtectiveMode)
   {
      // Only allow defensive management
      return;
   }
}

//+------------------------------------------------------------------+
void UpdatePositionInfo()
{
   g_PositionLots = 0;
   g_PositionEntryPrice = 0;
   g_PositionSL = 0;
   g_PositionTP = 0;
   g_PositionCurrentPrice = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   g_PositionProfit = 0;

   if(PositionSelect(Symbol()))
   {
      g_PositionLots = PositionGetDouble(POSITION_VOLUME);
      g_PositionEntryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      g_PositionSL = PositionGetDouble(POSITION_SL);
      g_PositionTP = PositionGetDouble(POSITION_TP);
      g_PositionType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      g_PositionProfit = PositionGetDouble(POSITION_PROFIT);
   }
}

//+------------------------------------------------------------------+
void DrawUIPanel()
{
   DeleteAllObjects(0, "GoldAI_");

   int x = g_PanelX, y = g_PanelY;
   int lineHeight = 18;

   CreateLabel("GoldAI_bg", x, y, g_PanelWidth, g_PanelHeight, g_ColorBg, g_ColorBg, "");

   y += 5;
   CreateLabel("GoldAI_header", x + 5, y, g_PanelWidth - 10, 20, g_ColorHeader, clrWhite, "Gold AI Trader EA", 10, true);
   y += 22;

   CreateLabel("GoldAI_sec1", x + 5, y, g_PanelWidth - 10, lineHeight, clrNONE, g_ColorHeader, "━━━ CONNECTION ━━━", 8, true);
   y += lineHeight;

   CreateLabel("GoldAI_status_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Status:");
   color statusColor = g_IsConnected ? g_ColorSuccess : g_ColorError;
   string statusText = g_IsConnected ? "Connected" : "Disconnected";
   CreateLabel("GoldAI_status_val", x + 120, y, 150, lineHeight, clrNONE, statusColor, statusText, 8, true);
   y += lineHeight;

   CreateLabel("GoldAI_lastpoll_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Last Poll:");
   string lastPollStr = (g_LastSuccessfulPoll > 0) ? TimeToString(g_LastSuccessfulPoll, TIME_SECONDS) : "Never";
   CreateLabel("GoldAI_lastpoll_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, lastPollStr);
   y += lineHeight;

   CreateLabel("GoldAI_http_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "HTTP Status:");
   string httpStr = (g_LastHttpCode > 0) ? IntegerToString(g_LastHttpCode) : "N/A";
   color httpColor = (g_LastHttpCode >= 200 && g_LastHttpCode < 300) ? g_ColorSuccess : g_ColorError;
   CreateLabel("GoldAI_http_val", x + 120, y, 150, lineHeight, clrNONE, httpColor, httpStr);
   y += lineHeight;

   CreateLabel("GoldAI_mode_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Mode:");
   string modeStr = Inp_ShadowMode ? "SHADOW" : (Inp_AllowTrading ? "LIVE" : "DEMO");
   color modeColor = Inp_ShadowMode ? g_ColorWarning : (Inp_AllowTrading ? g_ColorSuccess : g_ColorValue);
   CreateLabel("GoldAI_mode_val", x + 120, y, 150, lineHeight, clrNONE, modeColor, modeStr, 8, true);
   y += lineHeight;

   y += 5;
   CreateLabel("GoldAI_sec2", x + 5, y, g_PanelWidth - 10, lineHeight, clrNONE, g_ColorHeader, "━━━ LAST SIGNAL ━━━", 8, true);
   y += lineHeight;

   CreateLabel("GoldAI_sigid_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Signal ID:");
   CreateLabel("GoldAI_sigid_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, (g_LastSignalId != "") ? g_LastSignalId : "None");
   y += lineHeight;

   CreateLabel("GoldAI_action_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Action:");
   CreateLabel("GoldAI_action_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, (g_LastSignalAction != "") ? g_LastSignalAction : "N/A");
   y += lineHeight;

   CreateLabel("GoldAI_result_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Result:");
   color resultColor = (g_LastExecutionResult == "executed") ? g_ColorSuccess :
                       (g_LastExecutionResult == "failed") ? g_ColorError : g_ColorText;
   CreateLabel("GoldAI_result_val", x + 120, y, 150, lineHeight, clrNONE, resultColor, (g_LastExecutionResult != "") ? g_LastExecutionResult : "N/A");
   y += lineHeight;

   y += 5;
   CreateLabel("GoldAI_sec3", x + 5, y, g_PanelWidth - 10, lineHeight, clrNONE, g_ColorHeader, "━━━ ACCOUNT ━━━", 8, true);
   y += lineHeight;

   CreateLabel("GoldAI_account_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Account:");
   CreateLabel("GoldAI_account_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)));
   y += lineHeight;

   CreateLabel("GoldAI_server_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Server:");
   CreateLabel("GoldAI_server_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, AccountInfoString(ACCOUNT_SERVER));
   y += lineHeight;

   CreateLabel("GoldAI_symbol_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Symbol:");
   CreateLabel("GoldAI_symbol_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, Symbol());
   y += lineHeight;

   y += 5;
   CreateLabel("GoldAI_sec4", x + 5, y, g_PanelWidth - 10, lineHeight, clrNONE, g_ColorHeader, "━━━ POSITION ━━━", 8, true);
   y += lineHeight;

   if(g_PositionLots > 0)
   {
      string posTypeStr = (g_PositionType == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      color posColor = (g_PositionType == POSITION_TYPE_BUY) ? clrDodgerBlue : clrOrangeRed;

      CreateLabel("GoldAI_pos_side_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Side:");
      CreateLabel("GoldAI_pos_side_val", x + 120, y, 150, lineHeight, clrNONE, posColor, posTypeStr, 8, true);
      y += lineHeight;

      CreateLabel("GoldAI_pos_lots_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Lots:");
      CreateLabel("GoldAI_pos_lots_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, DoubleToString(g_PositionLots, 2));
      y += lineHeight;

      CreateLabel("GoldAI_pos_entry_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Entry:");
      CreateLabel("GoldAI_pos_entry_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, DoubleToString(g_PositionEntryPrice, _Digits));
      y += lineHeight;

      CreateLabel("GoldAI_pos_current_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "Current:");
      CreateLabel("GoldAI_pos_current_val", x + 120, y, 150, lineHeight, clrNONE, g_ColorValue, DoubleToString(g_PositionCurrentPrice, _Digits));
      y += lineHeight;

      CreateLabel("GoldAI_pos_profit_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "P&L:");
      color profitColor = (g_PositionProfit >= 0) ? g_ColorSuccess : g_ColorError;
      CreateLabel("GoldAI_pos_profit_val", x + 120, y, 150, lineHeight, clrNONE, profitColor, DoubleToString(g_PositionProfit, 2), 8, true);
      y += lineHeight;

      CreateLabel("GoldAI_pos_sl_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "SL:");
      CreateLabel("GoldAI_pos_sl_val", x + 120, y, 150, lineHeight, clrNONE, (g_PositionSL > 0) ? g_ColorValue : clrGray,
                  (g_PositionSL > 0) ? DoubleToString(g_PositionSL, _Digits) : "None");
      y += lineHeight;

      CreateLabel("GoldAI_pos_tp_lbl", x + 5, y, 100, lineHeight, clrNONE, g_ColorText, "TP:");
      CreateLabel("GoldAI_pos_tp_val", x + 120, y, 150, lineHeight, clrNONE, (g_PositionTP > 0) ? g_ColorValue : clrGray,
                  (g_PositionTP > 0) ? DoubleToString(g_PositionTP, _Digits) : "None");
   }
   else
   {
      CreateLabel("GoldAI_no_pos", x + 5, y, g_PanelWidth - 10, lineHeight * 2, clrNONE, clrGray, "No open position", 8, true);
   }

   ChartRedraw();
}

//+------------------------------------------------------------------+
void CreateLabel(string name, int x, int y, int width, int height, color bgColor, color textColor, string text, int fontSize=8, bool bold=false)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
   }

   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, width);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, height);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bgColor);
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);

   if(text != "")
   {
      string textObjName = name + "_text";
      if(ObjectFind(0, textObjName) < 0)
      {
         ObjectCreate(0, textObjName, OBJ_LABEL, 0, 0, 0);
         ObjectSetInteger(0, textObjName, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, textObjName, OBJPROP_BACK, false);
      }

      ObjectSetInteger(0, textObjName, OBJPROP_XDISTANCE, x + 3);
      ObjectSetInteger(0, textObjName, OBJPROP_YDISTANCE, y + 2);
      ObjectSetInteger(0, textObjName, OBJPROP_COLOR, textColor);
      ObjectSetInteger(0, textObjName, OBJPROP_FONTSIZE, fontSize);
      ObjectSetString(0, textObjName, OBJPROP_FONT, bold ? "Arial Bold" : "Arial");
      ObjectSetString(0, textObjName, OBJPROP_TEXT, text);
   }
}

//+------------------------------------------------------------------+
void DeleteAllObjects(long chartId, string prefix)
{
   int total = ObjectsTotal(chartId, 0, OBJ_LABEL);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(chartId, i, 0, OBJ_LABEL);
      if(StringSubstr(name, 0, StringLen(prefix)) == prefix)
         ObjectDelete(chartId, name);
   }

   total = ObjectsTotal(chartId, 0, OBJ_RECTANGLE_LABEL);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(chartId, i, 0, OBJ_RECTANGLE_LABEL);
      if(StringSubstr(name, 0, StringLen(prefix)) == prefix)
         ObjectDelete(chartId, name);
   }
}

//+------------------------------------------------------------------+
void StringToBuffer(string str, uchar &buffer[])
{
   int len = StringLen(str);
   ArrayResize(buffer, len);
   for(int i = 0; i < len; i++)
      buffer[i] = (uchar)StringGetCharacter(str, i);
}
//+------------------------------------------------------------------+
