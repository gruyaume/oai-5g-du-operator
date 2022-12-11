# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

import ops.testing
from lightkube.models.core_v1 import (
    LoadBalancerIngress,
    LoadBalancerStatus,
    Service,
    ServiceSpec,
)
from lightkube.models.core_v1 import ServiceStatus as K8sServiceStatus
from ops.model import ActiveStatus
from ops.pebble import ServiceInfo, ServiceStartup, ServiceStatus
from ops.testing import Harness

from charm import Oai5GDUOperatorCharm


class TestCharm(unittest.TestCase):
    @patch("lightkube.core.client.GenericSyncClient")
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports, service_type: None,
    )
    def setUp(self, patch_lightkube_client):
        ops.testing.SIMULATE_CAN_CONNECT = True
        self.model_name = "whatever"
        self.addCleanup(setattr, ops.testing, "SIMULATE_CAN_CONNECT", False)
        self.harness = Harness(Oai5GDUOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.set_model_name(name=self.model_name)
        self.harness.begin()

    def _create_cu_relation_with_valid_data(self):
        relation_id = self.harness.add_relation("fiveg-f1", "cu")
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="cu/0")

        cu_address = "5.6.7.8"
        cu_port = "1234"
        key_values = {
            "cu_address": cu_address,
            "cu_port": cu_port,
        }
        self.harness.update_relation_data(
            relation_id=relation_id, app_or_unit="cu", key_values=key_values
        )
        return cu_address, cu_port

    @patch("lightkube.Client.get")
    @patch("ops.model.Container.push")
    def test_given_amf_relation_contains_amf_info_when_amf_relation_joined_then_config_file_is_pushed(  # noqa: E501
        self, mock_push, patch_lightkube_client_get
    ):
        load_balancer_ip = "1.2.3.4"
        patch_lightkube_client_get.return_value = Service(
            spec=ServiceSpec(type="LoadBalancer"),
            status=K8sServiceStatus(
                loadBalancer=LoadBalancerStatus(ingress=[LoadBalancerIngress(ip=load_balancer_ip)])
            ),
        )
        self.harness.set_can_connect(container="du", val=True)
        cu_adress, cu_port = self._create_cu_relation_with_valid_data()
        mock_push.assert_called_with(
            path="/opt/oai-gnb/etc/gnb.conf",
            source='Active_gNBs = ( "oai-du-rfsim");\n'
            "# Asn1_verbosity, choice in: none, info, annoying\n"
            'Asn1_verbosity = "none";\n\n'
            "gNBs =\n"
            "(\n"
            " {\n"
            "    ////////// Identification parameters:\n"
            "    gNB_ID = 0xe00;\n\n"
            '#     cell_type =  "CELL_MACRO_GNB";\n\n'
            '    gNB_name  =  "oai-du-rfsim";\n\n'
            "    // Tracking area code, 0x0000 and 0xfffe are reserved values\n"
            "    tracking_area_code  =  1;\n"
            "    plmn_list = ({ mcc = 208; mnc = 99; mnc_length =2; snssaiList = ({ sst = 1, sd = 0x000001 }) });\n\n\n"  # noqa: E501, W505
            "    nr_cellid = 12345678L;\n\n"
            "    ////////// Physical parameters:\n\n"
            "    min_rxtxtime                                              = 6;\n"
            "    force_256qam_off = 1;\n\n"
            "    pdcch_ConfigSIB1 = (\n"
            "      {\n"
            "        controlResourceSetZero = 12;\n"
            "        searchSpaceZero = 0;\n"
            "      }\n"
            "    );\n\n"
            "    servingCellConfigCommon = (\n"
            "    {\n"
            " #spCellConfigCommon\n\n"
            "      physCellId                                                    = 0;\n\n"
            "#  downlinkConfigCommon\n"
            "    #frequencyInfoDL\n"
            "      # this is 3600 MHz + 43 PRBs@30kHz SCS (same as initial BWP)\n"
            "      absoluteFrequencySSB                                          = 641280;\n"  # noqa: E501, W505
            "      dl_frequencyBand                                                 = 78;\n"
            "      # this is 3600 MHz\n"
            "      dl_absoluteFrequencyPointA                                       = 640008;\n"  # noqa: E501, W505
            "      #scs-SpecificCarrierList\n"
            "        dl_offstToCarrier                                              = 0;\n"
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "        dl_subcarrierSpacing                                           = 1;\n"
            "        dl_carrierBandwidth                                            = 106;\n"  # noqa: E501, W505
            "     #initialDownlinkBWP\n"
            "      #genericParameters\n"
            "        # this is RBstart=27,L=48 (275*(L-1))+RBstart\n"
            "        initialDLBWPlocationAndBandwidth                               = 28875; # 6366 12925 12956 28875 12952\n"  # noqa: E501, W505
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "        initialDLBWPsubcarrierSpacing                                           = 1;\n"  # noqa: E501, W505
            "      #pdcch-ConfigCommon\n"
            "        initialDLBWPcontrolResourceSetZero                              = 12;\n"  # noqa: E501, W505
            "        initialDLBWPsearchSpaceZero                                             = 0;\n\n"  # noqa: E501, W505
            "  #uplinkConfigCommon\n"
            "     #frequencyInfoUL\n"
            "      ul_frequencyBand                                                 = 78;\n"
            "      #scs-SpecificCarrierList\n"
            "      ul_offstToCarrier                                              = 0;\n"
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "      ul_subcarrierSpacing                                           = 1;\n"
            "      ul_carrierBandwidth                                            = 106;\n"
            "      pMax                                                          = 20;\n"
            "     #initialUplinkBWP\n"
            "      #genericParameters\n"
            "        initialULBWPlocationAndBandwidth                            = 28875;\n"
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "        initialULBWPsubcarrierSpacing                                           = 1;\n"  # noqa: E501, W505
            "      #rach-ConfigCommon\n"
            "        #rach-ConfigGeneric\n"
            "          prach_ConfigurationIndex                                  = 98;\n"
            "#prach_msg1_FDM\n"
            "#0 = one, 1=two, 2=four, 3=eight\n"
            "          prach_msg1_FDM                                            = 0;\n"
            "          prach_msg1_FrequencyStart                                 = 0;\n"
            "          zeroCorrelationZoneConfig                                 = 13;\n"
            "          preambleReceivedTargetPower                               = -96;\n"
            "#preamblTransMax (0...10) = (3,4,5,6,7,8,10,20,50,100,200)\n"
            "          preambleTransMax                                          = 6;\n"
            "#powerRampingStep\n"
            "# 0=dB0,1=dB2,2=dB4,3=dB6\n"
            "        powerRampingStep                                            = 1;\n"
            "#ra_ReponseWindow\n"
            "#1,2,4,8,10,20,40,80\n"
            "        ra_ResponseWindow                                           = 4;\n"
            "#ssb_perRACH_OccasionAndCB_PreamblesPerSSB_PR\n"
            "#1=oneeighth,2=onefourth,3=half,4=one,5=two,6=four,7=eight,8=sixteen\n"
            "        ssb_perRACH_OccasionAndCB_PreamblesPerSSB_PR                = 4;\n"
            "#oneHalf (0..15) 4,8,12,16,...60,64\n"
            "        ssb_perRACH_OccasionAndCB_PreamblesPerSSB                   = 14;\n"
            "#ra_ContentionResolutionTimer\n"
            "#(0..7) 8,16,24,32,40,48,56,64\n"
            "        ra_ContentionResolutionTimer                                = 7;\n"
            "        rsrp_ThresholdSSB                                           = 19;\n"
            "#prach-RootSequenceIndex_PR\n"
            "#1 = 839, 2 = 139\n"
            "        prach_RootSequenceIndex_PR                                  = 2;\n"
            "        prach_RootSequenceIndex                                     = 1;\n"
            "        # SCS for msg1, can only be 15 for 30 kHz < 6 GHz, takes precendence over the one derived from prach-ConfigIndex\n"  # noqa: E501, W505
            "        #\n"
            "        msg1_SubcarrierSpacing                                      = 1,\n"
            "# restrictedSetConfig\n"
            "# 0=unrestricted, 1=restricted type A, 2=restricted type B\n"
            "        restrictedSetConfig                                         = 0,\n\n"
            "        msg3_DeltaPreamble                                          = 1;\n"
            "        p0_NominalWithGrant                                         =-90;\n\n"
            "# pucch-ConfigCommon setup :\n"
            "# pucchGroupHopping\n"
            "# 0 = neither, 1= group hopping, 2=sequence hopping\n"
            "        pucchGroupHopping                                           = 0;\n"
            "        hoppingId                                                   = 40;\n"
            "        p0_nominal                                                  = -90;\n"
            "# ssb_PositionsInBurs_BitmapPR\n"
            "# 1=short, 2=medium, 3=long\n"
            "      ssb_PositionsInBurst_PR                                       = 2;\n"
            "      ssb_PositionsInBurst_Bitmap                                   = 1;\n\n"
            "# ssb_periodicityServingCell\n"
            "# 0 = ms5, 1=ms10, 2=ms20, 3=ms40, 4=ms80, 5=ms160, 6=spare2, 7=spare1\n"
            "      ssb_periodicityServingCell                                    = 2;\n\n"
            "# dmrs_TypeA_position\n"
            "# 0 = pos2, 1 = pos3\n"
            "      dmrs_TypeA_Position                                           = 0;\n\n"
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "      subcarrierSpacing                                             = 1;\n\n\n "  # noqa: E501, W505
            " #tdd-UL-DL-ConfigurationCommon\n"
            "# subcarrierSpacing\n"
            "# 0=kHz15, 1=kHz30, 2=kHz60, 3=kHz120\n"
            "      referenceSubcarrierSpacing                                    = 1;\n"
            "      # pattern1\n"
            "      # dl_UL_TransmissionPeriodicity\n"
            "      # 0=ms0p5, 1=ms0p625, 2=ms1, 3=ms1p25, 4=ms2, 5=ms2p5, 6=ms5, 7=ms10\n"
            "      dl_UL_TransmissionPeriodicity                                 = 6;\n"
            "      nrofDownlinkSlots                                             = 7;\n"
            "      nrofDownlinkSymbols                                           = 6;\n"
            "      nrofUplinkSlots                                               = 2;\n"
            "      nrofUplinkSymbols                                             = 4;\n\n"
            "      ssPBCH_BlockPower                                             = -25;\n"
            "     }\n\n"
            "  );\n\n\n"
            "    # ------- SCTP definitions\n"
            "    SCTP :\n"
            "    {\n"
            "        # Number of streams to use in input/output\n"
            "        SCTP_INSTREAMS  = 2;\n"
            "        SCTP_OUTSTREAMS = 2;\n"
            "    };\n"
            "  }\n"
            ");\n\n"
            "MACRLCs = (\n"
            "  {\n"
            "    num_cc           = 1;\n"
            '    tr_s_preference  = "local_L1";\n'
            '    tr_n_preference  = "f1";\n'
            '    local_n_if_name = "eth0";\n'
            '    local_n_address = "1.2.3.4";\n'
            f'    remote_n_address = "{cu_adress}";\n'
            "    local_n_portc   = 500;\n"
            "    local_n_portd   = 2153;\n"
            "    remote_n_portc  = 501;\n"
            f"    remote_n_portd  = {cu_port};\n"
            "    pusch_TargetSNRx10          = 200;\n"
            "    pucch_TargetSNRx10          = 200;\n"
            "  }\n"
            ");\n\n"
            "L1s = (\n"
            "{\n"
            "  num_cc = 1;\n"
            '  tr_n_preference = "local_mac";\n'
            "  prach_dtx_threshold = 200;\n"
            "  pucch0_dtx_threshold = 150;\n"
            "  ofdm_offset_divisor = 8; #set this to UINT_MAX for offset 0\n"
            "}\n"
            ");\n\n"
            "RUs = (\n"
            "    {\n"
            '       local_rf       = "yes"\n'
            "         nb_tx          = 1\n"
            "         nb_rx          = 1\n"
            "         att_tx         = 0\n"
            "         att_rx         = 0;\n"
            "         bands          = [78];\n"
            "         max_pdschReferenceSignalPower = -27;\n"
            "         max_rxgain                    = 114;\n"
            "         eNB_instances  = [0];\n"
            "         #beamforming 1x4 matrix:\n"
            "         bf_weights = [0x00007fff, 0x0000, 0x0000, 0x0000];\n"
            '         clock_src = "internal";\n'
            "    }\n"
            ");\n\n"
            "THREAD_STRUCT = (\n"
            "  {\n"
            '    #three config for level of parallelism "PARALLEL_SINGLE_THREAD", "PARALLEL_RU_L1_SPLIT", or "PARALLEL_RU_L1_TRX_SPLIT"\n'  # noqa: E501, W505
            '    parallel_config    = "PARALLEL_SINGLE_THREAD";\n'
            '    #two option for worker "WORKER_DISABLE" or "WORKER_ENABLE"\n'
            '    worker_config      = "WORKER_ENABLE";\n'
            "  }\n"
            ");\nrfsimulator: {\n"
            'serveraddr = "server";\n'
            '    serverport = "4043";\n'
            '    options = (); #("saviq"); or/and "chanmod"\n'
            '    modelname = "AWGN";\n'
            '    IQfile = "/tmp/rfsimulator.iqs"\n'
            "}\n\n"
            "     log_config :\n"
            "     {\n"
            '       global_log_level                      ="info";\n'
            '       hw_log_level                          ="info";\n'
            '       phy_log_level                         ="info";\n'
            '       mac_log_level                         ="info";\n'
            '       rlc_log_level                         ="info";\n'
            '       pdcp_log_level                        ="info";\n'
            '       rrc_log_level                         ="info";\n'
            '       f1ap_log_level                         ="debug";\n'
            '       ngap_log_level                         ="debug";\n'
            "    };",
        )

    @patch("lightkube.Client.get")
    @patch("ops.model.Container.push")
    def test_given_amf_and_db_relation_are_set_when_config_changed_then_pebble_plan_is_created(  # noqa: E501
        self, _, patch_lightkube_client_get
    ):
        load_balancer_ip = "1.2.3.4"
        patch_lightkube_client_get.return_value = Service(
            spec=ServiceSpec(type="LoadBalancer"),
            status=K8sServiceStatus(
                loadBalancer=LoadBalancerStatus(ingress=[LoadBalancerIngress(ip=load_balancer_ip)])
            ),
        )
        self.harness.set_can_connect(container="du", val=True)
        self._create_cu_relation_with_valid_data()

        expected_plan = {
            "services": {
                "du": {
                    "override": "replace",
                    "summary": "du",
                    "command": "/opt/oai-gnb/bin/nr-softmodem -O /opt/oai-gnb/etc/gnb.conf --sa -E --rfsim --log_config.global_log_options level nocolor time",  # noqa: E501
                    "startup": "enabled",
                }
            },
        }
        self.harness.container_pebble_ready("du")
        updated_plan = self.harness.get_container_pebble_plan("du").to_dict()
        self.assertEqual(expected_plan, updated_plan)
        service = self.harness.model.unit.get_container("du").get_service("du")
        self.assertTrue(service.is_running())
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("lightkube.Client.get")
    @patch("ops.model.Container.get_service")
    def test_given_unit_is_leader_when_f1_relation_joined_then_du_relation_data_is_set(
        self, patch_get_service, patch_k8s_get
    ):
        load_balancer_ip = "5.6.7.8"
        patch_k8s_get.return_value = Service(
            spec=ServiceSpec(type="LoadBalancer"),
            status=K8sServiceStatus(
                loadBalancer=LoadBalancerStatus(ingress=[LoadBalancerIngress(ip=load_balancer_ip)])
            ),
        )
        self.harness.set_leader(True)
        self.harness.set_can_connect(container="du", val=True)
        patch_get_service.return_value = ServiceInfo(
            name="du",
            current=ServiceStatus.ACTIVE,
            startup=ServiceStartup.ENABLED,
        )

        relation_id = self.harness.add_relation(relation_name="fiveg-f1", remote_app="du")
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="du/0")

        relation_data = self.harness.get_relation_data(
            relation_id=relation_id, app_or_unit=self.harness.model.app.name
        )

        assert relation_data["du_address"] == load_balancer_ip
