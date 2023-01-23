## Agenda
When you deploy and remove a lot of virtual machines and segments using vCenter and NSX-T, sometimes it happens so when you try to delete the segments of removed virtual machines it throws an error, because NSX thinks they are still connected, and you need to open Postman to detach them manually making many api requests. I write a script which can help me to remove such segments.

## References
 - https://www.livefire.solutions/uncategorized/do-you-fail-to-delete-a-nsx-t-2-4-segment-or-logical-switch-via-simlified-ui-or-adanced-ui/
 - https://vkernel.nl/unable-to-delete-a-segment-in-nsx-t-3-x/

## Examples

```bash
nsx-t > ls --detach --name '^vRO_.+'
+----------------------------------------------------+----------------------------------------------------+-------+---------+
|                        Name                        |                         ID                         | Ports | Subnets |
+----------------------------------------------------+----------------------------------------------------+-------+---------+
|             vRO_ISP_CLI_IAkhnovetc.P.S             |             vRO_ISP_CLI_IAkhnovetc.P.S             |   0   |         |
|  vRO_ISP_CLI_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b  |  vRO_ISP_CLI_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b  |   0   |         |
|            vRO_ISP_RTR-L_IAkhnovetc.P.S            |            vRO_ISP_RTR-L_IAkhnovetc.P.S            |   0   |         |
| vRO_ISP_RTR-L_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b | vRO_ISP_RTR-L_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b |   0   |         |
|                vRO_ISP_RTR-L_sassas                |                vRO_ISP_RTR-L_sassas                |   0   |         |
|               vRO_ISP_RTR-L_sassas1                |               vRO_ISP_RTR-L_sassas1                |   0   |         |
|            vRO_ISP_RTR-R_IAkhnovetc.P.S            |            vRO_ISP_RTR-R_IAkhnovetc.P.S            |   0   |         |
| vRO_ISP_RTR-R_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b | vRO_ISP_RTR-R_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b |   0   |         |
|              vRO_RTR-L_IAkhnovetc.P.S              |              vRO_RTR-L_IAkhnovetc.P.S              |   0   |         |
|   vRO_RTR-L_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b   |   vRO_RTR-L_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b   |   0   |         |
|   vRO_RTR-R_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b   |   vRO_RTR-R_de47c0f0-2bc2-4d9c-ae6b-de1cea4dcf6b   |   0   |         |
+----------------------------------------------------+----------------------------------------------------+-------+---------+
```

```bash
nsx-t > describe vRO_SPB_Rachinskij.S.A
Display name: vRO_SPB_Rachinskij.S.A
ID: vRO_SPB_Rachinskij.S.A
Cretaed by: admin
+--------------------------------------+------------------------------------------------------------------+---------+
|                  ID                  |                               NAME                               |  Status |
+--------------------------------------+------------------------------------------------------------------+---------+
| 9d37c2cb-8cbc-4dd6-82a7-3b2476dcec00 | vRO_CLI2_Rachinskij.S.A.vmx@a21af37c-14dc-4f54-91ad-4ec54050c46a | SUCCESS |
| 85c924fa-3d1f-4c8f-8239-083e2122ce2a | vRO_DC2_Rachinskij.S.A.vmx@09c56f46-61ea-43b7-929a-27be4c79df49  |   DOWN  |
| 6a9b4324-22e8-4018-ad7b-3f4832b3a331 |  vRO_R2_Rachinskij.S.A.vmx@12777ca2-a119-4941-8e73-b8998622e737  |   DOWN  |
| 956ea633-4e61-4c98-812c-7928bbff0a06 | vRO_SRV2_Rachinskij.S.A.vmx@8e4a71ed-4604-4a38-9e65-848c305ea5a8 |   DOWN  |
+--------------------------------------+------------------------------------------------------------------+---------+
```

```bash
nsx-t > rm vRO_S_LAB_Win_0_Sarukhanov.R.B
Detach port vRO_CLI1_Sarukhanov.R.B.vmx@951a7105-104c-48aa-a7dd-e8d84fa6ea41
Removing vRO_S_LAB_Win_0_Sarukhanov.R.B...
Removing /infra/segments/vRO_S_LAB_Win_0_Sarukhanov.R.B/segment-discovery-profile-binding-maps/f965f452-0f04-4dc0-9db5-99c805fef20f - 200
Removing /infra/segments/vRO_S_LAB_Win_0_Sarukhanov.R.B/segment-security-profile-binding-maps/f965f452-0f04-4dc0-9db5-99c805fef20f - 200
vRO_S_LAB_Win_0_Sarukhanov.R.B is deleted
```