#pragma once

#include "exec.h"

#include <util/generic/fwd.h>
#include <util/generic/string.h>

class IOutputStream;
struct TCommandInfo;
struct TVars;

class TSubst2Shell: public TMultiCmdDescr, private ICommandSequenceWriter {
    TStringBuf OrigCmd;
    bool ForMSVS;

public:
    TSubst2Shell();
    IOutputStream& PrintAsLine(IOutputStream& out) const;
    // this might be somewhat inefficient
    TString PrintAsLine() const;

private:
    void Start(const TStringBuf& cmd, TString&) override;
    void StartCommand(TString&) override;
    void FinishCommand(TString& res) override;
    void Finish(TString& res, TCommandInfo&, const TVars&) override;
    ICommandSequenceWriter* Upgrade() override;

private:
    void BeginScript() override;
    void BeginCommand() override;
    void WriteArgument(TStringBuf arg) override;
    void WriteEnv(TStringBuf env) override;
    void EndCommand() override;
    void EndScript(TCommandInfo& cmdInfo, const TVars& vars) override;
    void PostScript(TVars& vars) override;
};
