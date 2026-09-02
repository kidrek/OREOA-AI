# Acquisition de disque

## Principe

L'acquisition de disque produit une image forensique : copie binaire integrale, empreintee, exploitable par les outils d'analyse. L'image est produite sans jamais modifier le disque source.

## Formats d'image

| Format | Description | Usage |
|--------|-------------|-------|
| raw (`.raw`, `.dd`) | image binaire brute, sans compression | analyse directe, compatible universel |
| E01 (`.E01`) | EnCase, avec compression et metadonnees | stockage, chaine de conservation |
| AFF4 (`.aff4`) | format ouvert, compression et metadonnees | stockage moderne |

## Commandes de reference

```bash
# Image raw via dd (source jamais montee en ecriture)
sudo dd if=/dev/sdX of=/mnt/usb/image.raw bs=4M status=progress conv=noerror,sync

# Image E01 via ewfacquire
sudo ewfacquire /dev/sdX -t /mnt/usb/image -f encase6

# Verification d'integrite
sha256sum /mnt/usb/image.raw
```

## Regles d'or

1. **Source jamais montee en ecriture** : le disque source est lu, jamais ecrit. Si un montage est necessaire, il est `:ro`.
2. **Une seule acquisition** : la premiere image est la reference ; les analyses s'effectuent sur des copies de la copie.
3. **Empreinte des deux cotes** : le SHA256 du disque source (si possible) et de l'image produite sont consignes et compares.
4. **Journal systématique** : chaque etape est horodatee dans le journal d'affaire.

## Chain of custody

Voir `templates/chaine-conservation.md` pour le registre de conservation standard.
