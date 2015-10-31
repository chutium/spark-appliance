```
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
aws iam create-role --role-name senza-create-spark --assume-role-policy-document file://$DIR/policy_trust.json
aws iam put-role-policy --role-name senza-create-spark --policy-name MintBucketAndSenzaCreate --policy-document file://$DIR/policy_senza_create.json
aws iam put-role-policy --role-name senza-create-spark --policy-name AssumeRoleByItSelf --policy-document file://$DIR/policy_assumerole.json
```


```
senza create https://raw.githubusercontent.com/zalando/ro2key/master/ro2key.yaml senzacreatespark \
             DockerImage=pierone.example.org/teamid/ro2key:0.3-SNAPSHOT \
             ApplicationID=teamid-ro2key \
             MintBucket=zalando-stups-mint-123456789-eu-west-1 \
             ScalyrAccountKey=xxxxxx-xxxx-xxxx-xxx \
             RolesArnPrefix="arn:aws:iam::123456789:role" \
             TargetRole=senza-create-spark \
             AuthURL="https://token.auth.example.org/access_token" \
             TokenInfoURL="https://auth.example.org/oauth2/tokeninfo" \
             Oauth2Scope="scope_for_ro2key" \
             HostedZone="teamid.example.org." \
             SSLCertificateId="arn:aws:iam::123456789:server-certificate/your_ssl_cert"
```


```
AWS_ACCESS_KEY_ID=id_of_mint_bucket_readonly_user AWS_SECRET_ACCESS_KEY=secret_key_of_mint_bucket_readonly_user AWS_SESSION_TOKEN="" aws s3 cp --region eu-west-1 s3://zalando-stups-mint-123456789-eu-west-1/teamid-ro2key/client.json .
AWS_ACCESS_KEY_ID=id_of_mint_bucket_readonly_user AWS_SECRET_ACCESS_KEY=secret_key_of_mint_bucket_readonly_user AWS_SESSION_TOKEN="" aws s3 cp --region eu-west-1 s3://zalando-stups-mint-123456789-eu-west-1/teamid-ro2key/user.json .

application_username=$(jq -r .application_username user.json)
application_password=$(jq -r .application_password user.json)
client_id=$(jq -r .client_id client.json)
client_secret=$(jq -r .client_secret client.json)

encoded_scopes="scope_for_ro2key"

encoded_application_password=$(python3 -c "import urllib.parse; print(urllib.parse.quote_plus('$application_password'))")

access_token=$(curl -u "$client_id:$client_secret" --silent -d "grant_type=password&username=$application_username&password=$encoded_application_password&scope=$encoded_scopes" https://auth.example.org/oauth2/access_token\?realm\=/services | jq -r .access_token)

key=$(curl -s --insecure --request GET --header "Authorization: Bearer $access_token" https://ro2key-senzacreatespark.example.org/get_key/senza-create-spark)
export AWS_ACCESS_KEY_ID=$(echo $key | jq .AccessKeyId -r)
export AWS_SECRET_ACCESS_KEY=$(echo $key | jq .SecretAccessKey -r)
export AWS_SESSION_TOKEN=$(echo $key | jq .SessionToken -r)
export AWS_DEFAULT_REGION="eu-west-1"

senza create https://raw.githubusercontent.com/zalando/spark-appliance/master/spark.yaml one \
             DockerImage=pierone.example.org/teamid/spark:1.5.3-SNAPSHOT \
             ApplicationID=teamid-spark \
             MintBucket=zalando-stups-mint-123456789-eu-west-1 \
             ScalyrAccountKey=xxxxxx-xxxx-xxxx-xxx \
             StartMaster=true \
             StartWorker=true \
             StartThriftServer=true \
             StartWebApp=true \
             HiveSite="s3://some-bucket-eu-west-1/hive-config/hive-site-mysql.xml" \
             ExtJars="s3://some-bucket-tmp-eu-west-1/libs/super-csv-2.2.0.jar" \
             AuthURL="https://token.auth.example.org/access_token" \
             TokenInfoURL="https://auth.example.org/oauth2/tokeninfo" \
             Oauth2Scope="scope_for_spark" \
             HostedZone="teamid.example.org." \
             SSLCertificateId="arn:aws:iam::123456789:server-certificate/your_ssl_cert" \
             InstanceType=m4.xlarge ExecutorMemory=12g
```
