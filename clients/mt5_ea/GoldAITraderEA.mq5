#property strict

input string ApiBase = "http://127.0.0.1/api/v1";
input string LicenseKey = "";
input string AccountServer = "";
input double Lots = 0.01;
string SessionToken = "";
string ProcessedSignalsFile = "processed_signals.csv";
bool ExpiryProtectiveMode = false;

int OnInit() {
  Print("[GoldAI] startup");
  RestoreSession();
  Authenticate();
  EventSetTimer(60); // lightweight supervision cadence
  return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason){
  PersistSession();
  EventKillTimer();
}

void OnTimer(){
  if(SessionToken=="") Authenticate();
  Heartbeat();
  PollSignals();
  SuperviseOpenPositions();
}

void RestoreSession(){ Print("[GoldAI] restore session state"); }
void PersistSession(){ Print("[GoldAI] persist session state"); }

void Authenticate(){
  Print("[GoldAI] auth request");
  // TODO: WebRequest POST /auth/activate and parse token
}

void Heartbeat(){
  Print("[GoldAI] heartbeat");
  // TODO: POST /auth/heartbeat; parse expiry/protective mode
}

void PollSignals(){
  Print("[GoldAI] poll signals");
  // TODO: GET /signals/poll and iterate signal list
  // for each signal:
  // 1) if duplicate -> log and skip
  // 2) if ExpiryProtectiveMode and is new entry -> block
  // 3) local safety checks (spread/max positions)
  // 4) execute market order with server-provided SL/TP
  // 5) persist processed signal id
  // 6) POST /execution/report
}

bool IsDuplicateSignal(string signal_id){
  int handle = FileOpen(ProcessedSignalsFile, FILE_READ|FILE_CSV|FILE_ANSI);
  if(handle != INVALID_HANDLE){
    while(!FileIsEnding(handle)){
      string line = FileReadString(handle);
      if(line == signal_id){ FileClose(handle); return true; }
    }
    FileClose(handle);
  }
  return false;
}

void MarkSignalProcessed(string signal_id){
  int handle = FileOpen(ProcessedSignalsFile, FILE_WRITE|FILE_READ|FILE_CSV|FILE_ANSI|FILE_SHARE_READ);
  if(handle == INVALID_HANDLE) return;
  FileSeek(handle, 0, SEEK_END);
  FileWrite(handle, signal_id);
  FileClose(handle);
}

void SuperviseOpenPositions(){
  // lightweight 1-minute breakeven/trailing checks only
  for(int i=PositionsTotal()-1; i>=0; i--){
    // TODO: fetch server directives and reconcile local position state
  }
}
