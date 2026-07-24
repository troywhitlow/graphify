{ Pascal/Delphi include fragment — no ASP delimiters, must stay on extract_pascal. }
const
  MaxBuffer = 4096;
  AppVersion = '1.0.0';

procedure LogMessage(const Msg: string);
begin
  WriteLn(Msg);
end;
