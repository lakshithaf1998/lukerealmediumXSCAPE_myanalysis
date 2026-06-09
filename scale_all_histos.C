#include <cmath>
#include <functional>
#include <cstdio>

#include "TFile.h"
#include "TKey.h"
#include "TDirectory.h"
#include "TH1.h"
#include "TList.h"
#include "TIter.h"
#include "TObject.h"
#include "TROOT.h"

void scale_all_histos(const char* path, double factor){
  if (!std::isfinite(factor)) {
    printf("[ERROR] scale_all_histos: non-finite factor for %s\n", path);
    return;
  }
  if (std::fabs(factor - 1.0) < 1e-15) return;

  TH1::AddDirectory(kFALSE);
  TFile f(path, "UPDATE");
  if (f.IsZombie()) { printf("[ERROR] Cannot open %s\n", path); return; }

  std::function<void(TDirectory*)> rec;
  rec = [&](TDirectory* d){
    TList* keys = (TList*)d->GetListOfKeys()->Clone();
    keys->SetOwner(kFALSE);
    TIter it(keys);

    while (TKey* k = (TKey*)it()) {
      TObject* o = k->ReadObj();
      if (!o) continue;

      if (o->InheritsFrom(TH1::Class())) {
        TH1* h = (TH1*)o;
        h->Scale(factor);
        d->cd();
        h->Write(h->GetName(), TObject::kOverwrite);
        delete h;
        gROOT->cd();
      } else if (o->InheritsFrom(TDirectory::Class())) {
        TDirectory* sub = (TDirectory*)o;
        d->cd(sub->GetName());
        rec(gDirectory);
        d->cd();
        delete sub;
      } else {
        delete o;
      }
    }
    delete keys;
  };

  rec(&f);
  f.Write();
  f.Close();
}
