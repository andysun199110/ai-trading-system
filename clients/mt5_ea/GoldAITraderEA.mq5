#property strict

input string ApiBase = "http://127.0.0.1/api/v1";
input string LicenseKey = "";
input string AccountServer = "";
string SessionToken = "";
string ProcessedSignalsFile = "processed_signals.csv";
bool ExpiryProtectiveMode = false;

int OnInit() {
  Print("[GoldAI] startup");
  Authenticate();
  EventSetTimer(15);
  return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason){ EventKillTimer(); }

void OnTimer(){
  if(SessionToken=="") Authenticate();
  Heartbeat();
  PollSignals();
}

void Authenticate(){
  Print("[GoldAI] auth request");
  // TODO: implement WebRequest POST /auth/activate and store token
}

void Heartbeat(){
  Print("[GoldAI] heartbeat");
  // TODO: POST /auth/heartbeat; set ExpiryProtectiveMode when expired
}

void PollSignals(){
  Print("[GoldAI] poll signals");
  // TODO: GET /signals/poll
  // 1) ignore duplicates by local file
  // 2) apply local safety checks
  // 3) block new entries on expiry
  // 4) allow protective actions for open positions when ExpiryProtectiveMode=true
}

bool IsDuplicateSignal(string signal_id){
  // TODO: persist/reload processed signal IDs from ProcessedSignalsFile
  return false;
}

void ReportExecution(string signal_id, string status){
  Print("[GoldAI] execution report: ", signal_id, " ", status);
  // TODO: POST /execution/report
}
