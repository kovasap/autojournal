#include <stdio.h>
#include <strings.h>
#include <iostream>
#include <cstring>
#include <zlib.h>  // -lz

std::string readz(gzFile zfd) { int c; std::string s;
  while((c=gzgetc(zfd))!=0 && c!=-1) s+=c;  return s;
}
int readi(gzFile zfd) { long r=0; gzread(zfd,&r,4); return r; }

int hdr(gzFile zfd) {
  int v, m, tc, ti, c;  char n[36];
  struct { int minfilter, foldlevel, prefs[10]; } x;
  v=readi(zfd);  m=readi(zfd);  tc=readi(zfd);  
  if (m != 0x50544646) { printf("invalid magic %08x\n", m);  return -1; }
  printf("version = %d;  tag count = %d\n", v, tc);
  for(ti=0; ti<tc; ti++) {
    gzread(zfd, n, 36);  c=*(int*)(n+32);  n[32]=0;
    printf("%u. c=%08x n=%s\n", ti, c, n);
  };  memset(&x, 0, sizeof x);  switch(v) {
    case 9: gzread(zfd, &x, 28); break;
    case 10: gzread(zfd, &x, 32); break;
    case 13: gzread(zfd, &x, 32); break;
    default: printf("Unknown db version\n"); return -1;
  }
  printf("minfilter=%d foldlevel=%d prefs=", x.minfilter, x.foldlevel);
  for(ti=0; ti<6; ti++) printf(" %d", x.prefs[ti]);  printf("\n");
  return 0;
}

void node(gzFile zfd, std::string np, int depth) {  std::string nodename, os;
  int tagindex, ishidden, numberofdays, di, d_d, d_m, d_y, numchildren, ni;
  char fmu[8], ts[200];  struct { unsigned short day, firstminuteused;
    int activeseconds, semiidleseconds, key, lmb, rmb, scrollwheel; } d;

  nodename=readz(zfd);  tagindex=readi(zfd);  ishidden=gzgetc(zfd);
  numberofdays=readi(zfd); os="";
  for(di=0; di<numberofdays; di++) { gzread(zfd, &d, sizeof d);
    d_d=d.day&31; d_m=(d.day>>5)&15; d_y=2000+(d.day>>9);
    snprintf(fmu, sizeof fmu, "%u:%02u", d.firstminuteused/60, d.firstminuteused%60);
    snprintf(ts, sizeof ts, " day=%u-%02u-%02u firstminuteused=%s activeseconds=%u\n",
      d_y, d_m, d_d, fmu, d.activeseconds);  os+=np+ts;
    snprintf(ts, sizeof ts, " semiidleseconds=%u key=%u lmb=%u rmb=%u scrollwheel=%u\n",
      d.semiidleseconds, d.key, d.lmb, d.rmb, d.scrollwheel);  os+=np+ts;
  }  numchildren=readi(zfd);
  if (!nodename.size()) {
    return;
  }
  printf("%snodename=%s tagindex=%u ishidden=%d numberofdays=%u numchildren=%u\n",
    np.c_str(), nodename.c_str(), tagindex, ishidden, numberofdays, numchildren);
  fputs(os.c_str(), stdout);  os="";
  // if (depth < 10) {
  for(ni=0; ni<numchildren; ni++) node(zfd, np+' ', depth + 1);
  // }
}

int main(int argc, char *argv[]) {  gzFile zfd;
  if (argc != 2) { printf("need 1 arg: PT file name\n");  return -1; }
  zfd=gzopen(argv[1], "rb");
  if(hdr(zfd)==-1) return -1;  node(zfd, "", 0);  gzclose_r(zfd);  return 0;
}
