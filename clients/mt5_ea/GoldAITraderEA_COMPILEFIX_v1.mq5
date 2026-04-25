//+------------------------------------------------------------------+
//|                                              GoldAITraderEA.mq5 |
//|                                    AI-Powered Gold Trading System |
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
input string Inp_AccountServer    = "";                                 // MT5 Server Name
input bool   Inp_ShadowMode       = true;                               // Shadow Mode (no execution)
input double Inp_DefaultLotSize   = 0.01;                               // Default Lot Size

input group "=== Risk Management ==="
input int    Inp_StopLossPoints   = 500;                                // Stop Loss (points)
input int    Inp_TakeProfitPoints = 1000;                               // Take Profit (points)
input bool   Inp_AllowTrading     = false;                              // Allow Live Trading (default: OFF)

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
   
   // Restore local state
   RestoreLocalState();
   
   // Initial authentication
   if(!Authenticate())
   {
      Print("[GoldAI] Initial auth failed, will retry on first poll");
      g_SessionToken = "";
   }
   
   // Set timer
   EventSetTimer(Inp_PollIntervalSec);
   
   Print("[GoldAI] Initialization complete");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   DeleteAllObjects(0, "GoldAI_");
   PrintFormat("[GoldAI] Deinitialized (reason: %d)", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Update position info
   UpdatePositionInfo();
   
   // Update UI
   DrawUIPanel();
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Ensure we have a session token
   if(g_SessionToken == "")
   {
      if(!Authenticate())
      {
         Print("[GoldAI] Auth failed, will retry");
         return;
      }
   }
   
   // Send heartbeat
   Heartbeat();
   
   // Poll for signals
   PollSignals();
   
   // Supervise positions
   SuperviseOpenPositions();
}

//+------------------------------------------------------------------+
//| Restore local state from file                                    |
//+------------------------------------------------------------------+
void RestoreLocalState()
{
   // Read processed signals file to avoid duplicates
   if(FileIsExist(g_ProcessedSignalsFile))
   {
      Print("[GoldAI] Restored processed signals ledger");
   }
   else
   {
      // Create file
      int handle = FileOpen(g_ProcessedSignalsFile, FILE_WRITE|FILE_CSV);
      if(handle != INVALID_HANDLE)
      {
         FileWrite(handle, "signal_id,timestamp,action,result");
         FileClose(handle);
      }
   }
}

//+------------------------------------------------------------------+
//| Authenticate with API server                                     |
//+------------------------------------------------------------------+
bool Authenticate()
{
   Print("[GoldAI] Authenticating...");
   
   string url = Inp_ApiBaseUrl + "/auth/activate";
   char postData[];
   string json = StringFormat("{\"license_key\":\"%s\",\"account_login\":\"%d\",\"account_server\":\"%s\"}", 
                              Inp_LicenseKey, 
                              AccountInfoInteger(ACCOUNT_LOGIN), 
                              AccountInfoString(ACCOUNT_SERVER));
   
   // Convert string to char array
   uchar ucharArray[];
   StringToBuffer(json, ucharArray);
   ArrayResize(postData, ArraySize(ucharArray));
   ArrayCopy(postData, ucharArray);
   
   char resultData[];
   string responseHeaders;
   
   // WebRequest: POST, URL, headers, timeout, postData, resultData, responseHeaders
   int resultCode = WebRequest("POST", url, NULL, 5000, postData, resultData, responseHeaders);
   
   g_LastHttpCode = resultCode;
   
   if(resultCode < 0)
   {
      g_LastHttpError = "HTTP Error: " + IntegerToString(resultCode);
      Print("[GoldAI] Auth failed: ", g_LastHttpError);
      g_IsConnected = false;
      return false;
   }
   
   string response = CharArrayToString(resultData);
   
   // Parse response (simple JSON parsing)
   if(StringFind(response, "\"token\"") > 0)
   {
      // Extract token
      int startPos = StringFind(response, "\"token\":\"") + 9;
      int endPos = StringFind(response, "\"", startPos);
      g_SessionToken = StringSubstr(response, startPos, endPos - startPos);
      
      g_IsConnected = true;
      g_LastHttpError = "";
      Print("[GoldAI] Auth successful");
      return true;
   }
   else
   {
      g_LastHttpError = "Invalid response";
      Print("[GoldAI] Auth failed: ", response);
      g_IsConnected = false;
      return false;
   }
}

//+------------------------------------------------------------------+
//| Send heartbeat to server                                         |
//+------------------------------------------------------------------+
void Heartbeat()
{
   if(g_SessionToken == "") return;
   
   string url = Inp_ApiBaseUrl + "/auth/heartbeat";
   char postData[];
   string json = StringFormat("{\"token\":\"%s\"}", g_SessionToken);
   
   uchar ucharArray[];
   StringToBuffer(json, ucharArray);
   ArrayResize(postData, ArraySize(ucharArray));
   ArrayCopy(postData, ucharArray);
   
   char resultData[];
   string responseHeaders;
   
   int resultCode = WebRequest("POST", url, NULL, 5000, postData, resultData, responseHeaders);
   
   if(resultCode < 0)
   {
      g_LastHttpCode = resultCode;
      g_LastHttpError = "Heartbeat failed";
      g_IsConnected = false;
   }
   else
   {
      g_LastHttpCode = resultCode;
      g_IsConnected = true;
   }
}

//+------------------------------------------------------------------+
//| Poll signals from server                                         |
//+------------------------------------------------------------------+
void PollSignals()
{
   if(g_SessionToken == "") return;
   
   g_LastPollTime = TimeCurrent();
   
   string url = Inp_ApiBaseUrl + "/signals/poll?token=" + g_SessionToken;
   
   char resultData[];
   string responseHeaders;
   
   int resultCode = WebRequest("GET", url, NULL, 5000, NULL, resultData, responseHeaders);
   
   g_LastHttpCode = resultCode;
   
   if(resultCode < 0)
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
   
   // Parse signals from response
   ProcessSignals(response);
}

//+------------------------------------------------------------------+
//| Process signals from API response                                |
//+------------------------------------------------------------------+
void ProcessSignals(string jsonResponse)
{
   // Simple JSON parsing for signals array
   if(StringFind(jsonResponse, "\"signals\":[]") > 0 || StringFind(jsonResponse, "\"signals\": []") > 0)
   {
      // No signals
      return;
   }
   
   // Extract signal_id
   int sigIdPos = StringFind(jsonResponse, "\"signal_id\":\"");
   if(sigIdPos < 0) return;
   
   int sigIdStart = sigIdPos + 13;
   int sigIdEnd = StringFind(jsonResponse, "\"", sigIdStart);
   string signalId = StringSubstr(jsonResponse, sigIdStart, sigIdEnd - sigIdStart);
   
   // Check if already processed
   if(IsDuplicateSignal(signalId))
   {
      return;
   }
   
   g_LastSignalId = signalId;
   
   // Extract action
   int actionPos = StringFind(jsonResponse, "\"action\":\"");
   if(actionPos < 0) return;
   
   int actionStart = actionPos + 10;
   int actionEnd = StringFind(jsonResponse, "\"", actionStart);
   string action = StringSubstr(jsonResponse, actionStart, actionEnd - actionStart);
   
   g_LastSignalAction = action;
   
   // Extract payload details
   double volume = Inp_DefaultLotSize;
   string side = "buy";
   double sl = 0, tp = 0;
   
   // Parse volume
   int volPos = StringFind(jsonResponse, "\"volume\":");
   if(volPos > 0)
   {
      int volStart = volPos + 9;
      int volEnd = StringFind(jsonResponse, ",", volStart);
      if(volEnd < 0) volEnd = StringFind(jsonResponse, "}", volStart);
      string volStr = StringSubstr(jsonResponse, volStart, volEnd - volStart);
      volume = StringToDouble(volStr);
   }
   
   // Parse side
   int sidePos = StringFind(jsonResponse, "\"side\":\"");
   if(sidePos > 0)
   {
      int sideStart = sidePos + 8;
      int sideEnd = StringFind(jsonResponse, "\"", sideStart);
      side = StringSubstr(jsonResponse, sideStart, sideEnd - sideStart);
   }
   
   // Execute signal
   if(Inp_ShadowMode)
   {
      PrintFormat("[GoldAI] SHADOW MODE: Would execute %s %s %.2f lots", action, side, volume);
      g_LastExecutionResult = "shadow_skipped";
      MarkSignalProcessed(signalId, action, "shadow_skipped");
   }
   else if(!Inp_AllowTrading)
   {
      PrintFormat("[GoldAI] Trading disabled: %s %s %.2f lots", action, side, volume);
      g_LastExecutionResult = "trading_disabled";
      MarkSignalProcessed(signalId, action, "trading_disabled");
   }
   else
   {
      // Execute trade
      bool success = ExecuteTrade(action, side, volume, sl, tp, signalId);
      g_LastExecutionResult = success ? "executed" : "failed";
      MarkSignalProcessed(signalId, action, g_LastExecutionResult);
      
      // Report execution
      ReportExecution(signalId, g_LastExecutionResult);
   }
}

//+------------------------------------------------------------------+
//| Execute trade                                                    |
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
   else if(action == "close")
   {
      // Close all positions for this symbol
      return CloseAllPositions();
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| Close all positions                                              |
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
//| Check if signal already processed                                |
//+------------------------------------------------------------------+
bool IsDuplicateSignal(string signalId)
{
   if(!FileIsExist(g_ProcessedSignalsFile)) return false;
   
   int handle = FileOpen(g_ProcessedSignalsFile, FILE_READ|FILE_CSV);
   if(handle == INVALID_HANDLE) return false;
   
   while(!FileIsEnding(handle))
   {
      string line = FileReadString(handle);
      if(StringFind(line, signalId) > 0)
      {
         FileClose(handle);
         return true;
      }
   }
   
   FileClose(handle);
   return false;
}

//+------------------------------------------------------------------+
//| Mark signal as processed                                         |
//+------------------------------------------------------------------+
void MarkSignalProcessed(string signalId, string action, string result)
{
   int handle = FileOpen(g_ProcessedSignalsFile, FILE_WRITE|FILE_CSV|FILE_APPEND);
   if(handle != INVALID_HANDLE)
   {
      FileWrite(handle, signalId, TimeToString(TimeCurrent()), action, result);
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
//| Report execution to server                                       |
//+------------------------------------------------------------------+
void ReportExecution(string signalId, string status)
{
   if(g_SessionToken == "") return;
   
   string url = Inp_ApiBaseUrl + "/execution/report";
   char postData[];
   string json = StringFormat("{\"token\":\"%s\",\"signal_id\":\"%s\",\"status\":\"%s\",\"payload\":{}}", 
                              g_SessionToken, signalId, status);
   
   uchar ucharArray[];
   StringToBuffer(json, ucharArray);
   ArrayResize(postData, ArraySize(ucharArray));
   ArrayCopy(postData, ucharArray);
   
   char resultData[];
   string responseHeaders;
   
   WebRequest("POST", url, NULL, 5000, postData, resultData, responseHeaders);
}

//+------------------------------------------------------------------+
//| Supervise open positions                                         |
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
//| Update position information                                      |
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
//| Draw UI Panel                                                    |
//+------------------------------------------------------------------+
void DrawUIPanel()
{
   DeleteAllObjects(0, "GoldAI_");
   
   int x = g_PanelX, y = g_PanelY;
   int lineHeight = 18;
   
   // Background
   CreateLabel("GoldAI_bg", x, y, g_PanelWidth, g_PanelHeight, g_ColorBg, g_ColorBg, "");
   
   // Header
   y += 5;
   CreateLabel("GoldAI_header", x + 5, y, g_PanelWidth - 10, 20, g_ColorHeader, clrWhite, "Gold AI Trader EA", 10, true);
   y += 22;
   
   // Connection Status
   CreateLabel("GoldAI_sec1", x + 5, y, g_PanelWidth - 10, lineHeight, CLR_NONE, g_ColorHeader, "━━━ CONNECTION ━━━", 8, true);
   y += lineHeight;
   
   CreateLabel("GoldAI_status_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Status:");
   color statusColor = g_IsConnected ? g_ColorSuccess : g_ColorError;
   string statusText = g_IsConnected ? "Connected" : "Disconnected";
   CreateLabel("GoldAI_status_val", x + 120, y, 150, lineHeight, CLR_NONE, statusColor, statusText, 8, true);
   y += lineHeight;
   
   CreateLabel("GoldAI_lastpoll_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Last Poll:");
   string lastPollStr = (g_LastSuccessfulPoll > 0) ? TimeToString(g_LastSuccessfulPoll, TIME_SECONDS) : "Never";
   CreateLabel("GoldAI_lastpoll_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, lastPollStr);
   y += lineHeight;
   
   CreateLabel("GoldAI_http_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "HTTP Status:");
   string httpStr = (g_LastHttpCode > 0) ? IntegerToString(g_LastHttpCode) : "N/A";
   color httpColor = (g_LastHttpCode >= 200 && g_LastHttpCode < 300) ? g_ColorSuccess : g_ColorError;
   CreateLabel("GoldAI_http_val", x + 120, y, 150, lineHeight, CLR_NONE, httpColor, httpStr);
   y += lineHeight;
   
   CreateLabel("GoldAI_mode_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Mode:");
   string modeStr = Inp_ShadowMode ? "SHADOW" : (Inp_AllowTrading ? "LIVE" : "DEMO");
   color modeColor = Inp_ShadowMode ? g_ColorWarning : (Inp_AllowTrading ? g_ColorSuccess : g_ColorValue);
   CreateLabel("GoldAI_mode_val", x + 120, y, 150, lineHeight, CLR_NONE, modeColor, modeStr, 8, true);
   y += lineHeight;
   
   // Signal Info
   y += 5;
   CreateLabel("GoldAI_sec2", x + 5, y, g_PanelWidth - 10, lineHeight, CLR_NONE, g_ColorHeader, "━━━ LAST SIGNAL ━━━", 8, true);
   y += lineHeight;
   
   CreateLabel("GoldAI_sigid_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Signal ID:");
   CreateLabel("GoldAI_sigid_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, (g_LastSignalId != "") ? g_LastSignalId : "None");
   y += lineHeight;
   
   CreateLabel("GoldAI_action_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Action:");
   CreateLabel("GoldAI_action_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, (g_LastSignalAction != "") ? g_LastSignalAction : "N/A");
   y += lineHeight;
   
   CreateLabel("GoldAI_result_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Result:");
   color resultColor = (g_LastExecutionResult == "executed") ? g_ColorSuccess : 
                       (g_LastExecutionResult == "failed") ? g_ColorError : g_ColorText;
   CreateLabel("GoldAI_result_val", x + 120, y, 150, lineHeight, CLR_NONE, resultColor, (g_LastExecutionResult != "") ? g_LastExecutionResult : "N/A");
   y += lineHeight;
   
   // Account Info
   y += 5;
   CreateLabel("GoldAI_sec3", x + 5, y, g_PanelWidth - 10, lineHeight, CLR_NONE, g_ColorHeader, "━━━ ACCOUNT ━━━", 8, true);
   y += lineHeight;
   
   CreateLabel("GoldAI_account_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Account:");
   CreateLabel("GoldAI_account_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)));
   y += lineHeight;
   
   CreateLabel("GoldAI_server_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Server:");
   CreateLabel("GoldAI_server_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, AccountInfoString(ACCOUNT_SERVER));
   y += lineHeight;
   
   CreateLabel("GoldAI_symbol_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Symbol:");
   CreateLabel("GoldAI_symbol_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, Symbol());
   y += lineHeight;
   
   // Position Info
   y += 5;
   CreateLabel("GoldAI_sec4", x + 5, y, g_PanelWidth - 10, lineHeight, CLR_NONE, g_ColorHeader, "━━━ POSITION ━━━", 8, true);
   y += lineHeight;
   
   if(g_PositionLots > 0)
   {
      string posTypeStr = (g_PositionType == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      color posColor = (g_PositionType == POSITION_TYPE_BUY) ? clrDodgerBlue : clrOrangeRed;
      
      CreateLabel("GoldAI_pos_side_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Side:");
      CreateLabel("GoldAI_pos_side_val", x + 120, y, 150, lineHeight, CLR_NONE, posColor, posTypeStr, 8, true);
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_lots_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Lots:");
      CreateLabel("GoldAI_pos_lots_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, DoubleToString(g_PositionLots, 2));
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_entry_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Entry:");
      CreateLabel("GoldAI_pos_entry_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, DoubleToString(g_PositionEntryPrice, _Digits));
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_current_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "Current:");
      CreateLabel("GoldAI_pos_current_val", x + 120, y, 150, lineHeight, CLR_NONE, g_ColorValue, DoubleToString(g_PositionCurrentPrice, _Digits));
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_profit_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "P&L:");
      color profitColor = (g_PositionProfit >= 0) ? g_ColorSuccess : g_ColorError;
      CreateLabel("GoldAI_pos_profit_val", x + 120, y, 150, lineHeight, CLR_NONE, profitColor, DoubleToString(g_PositionProfit, 2), 8, true);
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_sl_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "SL:");
      CreateLabel("GoldAI_pos_sl_val", x + 120, y, 150, lineHeight, CLR_NONE, (g_PositionSL > 0) ? g_ColorValue : clrGray, 
                  (g_PositionSL > 0) ? DoubleToString(g_PositionSL, _Digits) : "None");
      y += lineHeight;
      
      CreateLabel("GoldAI_pos_tp_lbl", x + 5, y, 100, lineHeight, CLR_NONE, g_ColorText, "TP:");
      CreateLabel("GoldAI_pos_tp_val", x + 120, y, 150, lineHeight, CLR_NONE, (g_PositionTP > 0) ? g_ColorValue : clrGray, 
                  (g_PositionTP > 0) ? DoubleToString(g_PositionTP, _Digits) : "None");
   }
   else
   {
      CreateLabel("GoldAI_no_pos", x + 5, y, g_PanelWidth - 10, lineHeight * 2, CLR_NONE, clrGray, "No open position", 8, true);
   }
   
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Helper: Create Label                                             |
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
//| Helper: Delete Objects                                           |
//+------------------------------------------------------------------+
void DeleteAllObjects(long chartId, string prefix)
{
   int total = ObjectsTotal(chartId, 0, OBJ_LABEL);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(chartId, i, 0, OBJ_LABEL);
      if(StringSubstr(name, 0, StringLen(prefix)) == prefix)
      {
         ObjectDelete(chartId, name);
      }
   }
   
   total = ObjectsTotal(chartId, 0, OBJ_RECTANGLE_LABEL);
   for(int i = total - 1; i >= 0; i--)
   {
      string name = ObjectName(chartId, i, 0, OBJ_RECTANGLE_LABEL);
      if(StringSubstr(name, 0, StringLen(prefix)) == prefix)
      {
         ObjectDelete(chartId, name);
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: String to Buffer                                         |
//+------------------------------------------------------------------+
void StringToBuffer(string str, uchar &buffer[])
{
   int len = StringLen(str);
   ArrayResize(buffer, len);
   for(int i = 0; i < len; i++)
   {
      buffer[i] = (uchar)StringGetCharacter(str, i);
   }
}
//+------------------------------------------------------------------+
