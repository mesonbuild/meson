#include <pcap/pcap.h>

int
main()
{
    char errbuf[PCAP_ERRBUF_SIZE];
    pcap_t *p = pcap_create(NULL, errbuf);
    return p == NULL;
}
